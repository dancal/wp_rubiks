from tkinter import ttk
from queue import Queue
from queue import Empty
from time import sleep
from PIL import ImageTk, Image, ImageDraw
import argparse
from sklearn.cluster import KMeans
from operator import itemgetter
from collections import Counter

import numpy
import random
import tkinter as tk
import threading as td
import cv2
import numpy as np
import arms
import pivotpi as pp
import kociemba
import io
import os
import os.path
import json
import transitions
import logging
import sys
import webcolors

from sklearn.cluster import KMeans
from scipy.spatial import distance
import itertools

try:
    from color_detector import ColorCalibrator, ColorMatcher, ImageProcessor, StabilityChecker
    COLOR_DETECTOR_AVAILABLE = True
except ImportError:
    COLOR_DETECTOR_AVAILABLE = False

import re

# 6면체 큐브의 기준 색상 (LAB 색 공간, 예시값)
REFERENCE_COLORS = [
    [255, 255, 255],  # White
    [0, 155, 72],  # Green
    [0, 70, 173],  # Blue
    [183, 18, 52],  # Red
    [255, 213, 0],  # Yellow
    [255, 88, 0],  # Orange
]

def rgb_to_lab(rgb):
    rgb_arr = np.asarray(rgb, dtype=np.float32)
    rgb_arr = np.clip(rgb_arr, 0, 255).astype(np.uint8)
    lab = cv2.cvtColor(rgb_arr.reshape(1, 1, 3), cv2.COLOR_RGB2LAB)
    return lab.reshape(3).astype(np.float32)

def cluster_colors(colors_lab, n_colors=6):
    colors_lab = np.asarray(colors_lab, dtype=np.float32)
    if colors_lab.ndim != 2 or colors_lab.shape[1] != 3:
        raise ValueError('colors_lab must be an Nx3 array')
    kmeans = KMeans(n_clusters=n_colors, n_init=10, random_state=0)
    kmeans.fit(colors_lab)
    return kmeans.cluster_centers_.astype(np.float32), kmeans.labels_.astype(int)

def match_colors(cluster_centers_lab, reference_colors_rgb):
    reference_colors_rgb = np.asarray(reference_colors_rgb, dtype=np.float32)
    reference_lab = np.vstack([rgb_to_lab(rgb) for rgb in reference_colors_rgb])
    cluster_centers_lab = np.asarray(cluster_centers_lab, dtype=np.float32)
    d = distance.cdist(cluster_centers_lab, reference_lab, metric='euclidean')
    nearest = np.argmin(d, axis=1)
    return [tuple(map(int, reference_colors_rgb[i])) for i in nearest]

def rgb_array_to_lab(rgb_array):
    rgb = np.asarray(rgb_array, dtype=np.float32)
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    if rgb.ndim != 2 or rgb.shape[1] != 3:
        raise ValueError('rgb_array must be an Nx3 array')
    lab = cv2.cvtColor(rgb.reshape(-1, 1, 3), cv2.COLOR_RGB2LAB)
    return lab.reshape(-1, 3).astype(np.float32)


# Kociemba corner and edge facelet definitions (0-indexed)
# U=0-8, R=9-17, F=18-26, D=27-35, L=36-44, B=45-53
_CORNER_FACELETS = [
    [8, 9, 20], [6, 18, 38], [0, 36, 47], [2, 45, 11],
    [29, 26, 15], [27, 44, 24], [33, 53, 42], [35, 17, 51],
]
_EDGE_FACELETS = [
    [5, 10], [7, 19], [3, 37], [1, 46],
    [32, 16], [28, 25], [30, 43], [34, 52],
    [23, 12], [21, 41], [50, 39], [48, 14],
]
# Valid corner color sets (URFDLB label indices: 0=U,1=R,2=F,3=D,4=L,5=B)
_VALID_CORNERS = [
    frozenset({0, 1, 2}), frozenset({0, 2, 4}), frozenset({0, 4, 5}), frozenset({0, 5, 1}),
    frozenset({3, 2, 1}), frozenset({3, 4, 2}), frozenset({3, 5, 4}), frozenset({3, 1, 5}),
]
_VALID_EDGES = [
    frozenset({0, 1}), frozenset({0, 2}), frozenset({0, 4}), frozenset({0, 5}),
    frozenset({1, 2}), frozenset({2, 4}), frozenset({4, 5}), frozenset({5, 1}),
    frozenset({3, 1}), frozenset({3, 2}), frozenset({3, 4}), frozenset({3, 5}),
]


def _check_corners_edges(labels):
    """Check if all corners and edges form valid pieces (no duplicates)."""
    seen_corners = set()
    for facelets in _CORNER_FACELETS:
        corner = frozenset(labels[f] for f in facelets)
        if corner not in _VALID_CORNERS or corner in seen_corners:
            return False
        seen_corners.add(corner)
    seen_edges = set()
    for facelets in _EDGE_FACELETS:
        edge = frozenset(labels[f] for f in facelets)
        if edge not in _VALID_EDGES or edge in seen_edges:
            return False
        seen_edges.add(edge)
    return True


def correct_color_classification(labels, dists, cube_centers_when_flat):
    """
    Correct color misclassifications using cube validity constraints.
    When the distribution is unbalanced (e.g., too many red, too few orange),
    try flipping borderline stickers from the over-represented color to the
    under-represented color. Uses corner/edge validity and kociemba solver
    to verify the corrected state.
    :param labels: array of 54 label indices (0-5)
    :param dists: 54x6 distance matrix from each sticker to each center
    :param cube_centers_when_flat: indices of center stickers
    :return: corrected labels array
    """
    labels = labels.copy()
    kociemba_map = {0: 'U', 1: 'R', 2: 'F', 3: 'D', 4: 'L', 5: 'B'}

    # Check if already balanced and valid
    counts = Counter(labels)
    if len(counts) == 6 and set(counts.values()) == {9}:
        if _check_corners_edges(labels):
            ks = ''.join(kociemba_map[l] for l in labels)
            try:
                kociemba.solve(ks)
                return labels  # Valid, no correction needed
            except Exception:
                pass  # Fall through to correction

    # Find over-represented and under-represented colors
    target = 9
    over_colors = [c for c in range(6) if counts.get(c, 0) > target]
    under_colors = [c for c in range(6) if counts.get(c, 0) < target]

    if not over_colors or not under_colors:
        return labels  # Can't fix

    # Find all flip candidates: stickers where the over_color is closest
    # and an under_color is the second closest
    flip_candidates_by_pair = {}  # (over_c, under_c) -> list of (idx, margin)
    for over_c in over_colors:
        for under_c in under_colors:
            for i in range(54):
                if i in cube_centers_when_flat:
                    continue
                if labels[i] != over_c:
                    continue
                sorted_idx = np.argsort(dists[i])
                if sorted_idx[1] == under_c:
                    margin = dists[i][under_c] - dists[i][over_c]
                    flip_candidates_by_pair.setdefault((over_c, under_c), []).append((i, margin))

    # Sort each pair's candidates by margin (smallest first)
    for pair, cands in flip_candidates_by_pair.items():
        cands.sort(key=lambda x: x[1])

    # Generate all possible distributions of excess among under_colors
    def generate_distributions(excess, under_list, available_per_under):
        """Generate all ways to distribute `excess` flips among under_list colors."""
        if excess == 0:
            yield {}
            return
        if not under_list:
            return
        under = under_list[0]
        rest = under_list[1:]
        max_for_this = min(excess, available_per_under.get(under, 0))
        for n in range(max_for_this + 1):
            remaining = excess - n
            new_avail = dict(available_per_under)
            new_avail[under] = new_avail.get(under, 0) - n
            for dist in generate_distributions(remaining, rest, new_avail):
                result = dict(dist)
                if n > 0:
                    result[under] = n
                yield result

    # For each over_color, generate all possible distributions
    over_distributions = []
    for over_c in over_colors:
        excess = counts[over_c] - target
        available = {}
        for under_c in under_colors:
            pair = (over_c, under_c)
            available[under_c] = len(flip_candidates_by_pair.get(pair, []))
        dists_for_over = list(generate_distributions(excess, under_colors, available))
        over_distributions.append((over_c, dists_for_over))

    # Try all combinations of distributions across over_colors
    for dist_combo in itertools.product(*[d for _, d in over_distributions]):
        # Build the flip plan from this distribution combo
        flip_plan = {}
        for (over_c, _), dist in zip(over_distributions, dist_combo):
            for under_c, n_flip in dist.items():
                if n_flip > 0:
                    flip_plan[(over_c, under_c)] = n_flip

        if not flip_plan:
            continue

        # Check we have enough candidates for each pair
        valid_plan = True
        pair_combos = []
        for pair, n_flip in flip_plan.items():
            candidates = flip_candidates_by_pair.get(pair, [])
            if len(candidates) < n_flip:
                valid_plan = False
                break
            pair_combos.append(list(itertools.combinations(candidates, n_flip)))
        if not valid_plan:
            continue

        # Try all combinations of specific stickers to flip
        for combo in itertools.product(*pair_combos):
            test_labels = labels.copy()
            for pair_idx, pair_flips in enumerate(combo):
                pair = list(flip_plan.keys())[pair_idx]
                under_c = pair[1]
                for (idx, margin) in pair_flips:
                    test_labels[idx] = under_c

            # Check distribution
            tc = Counter(test_labels)
            if len(tc) != 6 or set(tc.values()) != {9}:
                continue

            # Check corners and edges
            if not _check_corners_edges(test_labels):
                continue

            # Check kociemba
            ks = ''.join(kociemba_map[l] for l in test_labels)
            try:
                kociemba.solve(ks)
                n_flipped = sum(len(pf) for pf in combo)
                logger.info(f'Color classification corrected: {n_flipped} stickers flipped')
                return test_labels
            except Exception:
                continue

    # If no valid combination found, return original labels
    logger.warning('Could not find valid color correction via cube validity constraints')
    return labels

class QueuePubSub():
    '''
    Class that implements the notion of subscribers/publishers by using standard queues
    '''
    def __init__(self, queues):
        self.queues = queues

    def publish(self, channel, message):
        '''
        channel - An immutable key that represents the name of the channel. It can be nonexistent.
        message - The message that will be pushed to the queue that's associated to the given channel.
        '''
        if channel not in self.queues:
            self.queues[channel] = Queue()
        self.queues[channel].put(message)
    
    def subscribe(self, channel):
        '''
        channel - An immutable key that represents the name of the channel. It can be nonexistent.
        '''
        if channel not in self.queues:
            self.queues[channel] = Queue()
        return self.queues[channel]

# generic page that can be brought onto the front plane
class Page(tk.Frame):
    def __init__(self, *args, **kwargs):
        super(Page, self).__init__(*args, **kwargs)
        self.place(x=0, y=0, relwidth=1.0, relheight=1.0)

    def show(self):
        self.lift()


class Solver(Page):

    def _from_rgb(self,rgb):
        return "#%02x%02x%02x" % rgb

    def get_cube_row_col(self,sname):

        row = 0
        col = 0
        if sname == 'F':
            row = 0
            col = 0
        elif sname == 'R':
            row = 0
            col = 1
        elif sname == 'B':
            row = 0
            col = 2
        elif sname == 'U':
            row = 1
            col = 0
        elif sname == 'D':
            row = 1
            col = 1
        elif sname == 'L':
            row = 1
            col = 2
        return [row, col]

    def show_frame(self):
        isbusy	= camera.IsBusy()
        if isbusy:
            self.after(10, self.show_frame)
        else:
            scale       	= 2.5
            v_width    		= int(640 / scale)
            v_height 		= int(480 / scale)
            ok, frame 		= camera.cam.read()
            if ok:
                with camera.lock:
                    camera.cv_image	= cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) 
                img				= Image.fromarray(camera.cv_image).resize((v_width,v_height))
                imgtk 			= ImageTk.PhotoImage(image=img)
                self.display1.imgtk = imgtk #Shows frame for display 1
                self.display1.configure(image=imgtk)
                self.after(30, self.show_frame)
            else:
                self.after(10, self.show_frame)
        
    def show_scan_cube_status(self):

        # Map face name to capture index (capture order: F, L, B, R, U, D)
        capture_index = {'F': 0, 'L': 1, 'B': 2, 'R': 3, 'U': 4, 'D': 5}

        # Check if classification is complete (all 6 faces have labels)
        classification_done = all(
            camera.cubeLabels[cap_i][1][1] != ''
            for cap_i in capture_index.values()
        )
        if classification_done and not getattr(self, '_classification_logged', False):
            self._classification_logged = True
            logger.info(f'show_scan_cube_status: classification_done=True, '
                        f'cubeLabels centers: {[camera.cubeLabels[i][1][1] for i in range(6)]}')

        # Representative colors for each classified label (URFDLB)
        # Use center sticker RGB of each face as the representative color.
        # capture_index maps face name -> capture index, and the face name
        # is the same as the URFDLB label for that face.
        label_colors = {}
        if classification_done:
            for cap_name, cap_i in capture_index.items():
                center_rgb = camera.cubeColors[cap_i][1][1]
                if center_rgb:
                    label_colors[cap_name] = center_rgb
            logger.debug(f'cubeLabels[0][1][1]={camera.cubeLabels[0][1][1]}, '
                        f'label_colors keys={list(label_colors.keys())}, '
                        f'classification_done={classification_done}')

        for idx, sname in enumerate(self.cubeScanList):
            cap_idx = capture_index.get(sname, idx)
            for crow in range(3):
                for ccol in range(3):
                    if camera.cubeColors[cap_idx][crow][ccol]:
                        cls_label = camera.cubeLabels[cap_idx][crow][ccol]

                        if classification_done and cls_label and cls_label in label_colors:
                            # After classification: use representative color (6 colors only)
                            bg_rgb = label_colors[cls_label]
                            label_text = cls_label
                            fg_color = 'white'
                        else:
                            # Before/during classification: show raw RGB color
                            bg_rgb = camera.cubeColors[cap_idx][crow][ccol]
                            label_text = cls_label if cls_label else ''
                            fg_color = 'black'

                        if crow == 1 and ccol == 1:
                            label_text = sname

                        colorname = webcolors.rgb_percent_to_rgb(webcolors.rgb_to_rgb_percent(bg_rgb))
                        self.cubematrix[idx][crow][ccol].config(text=label_text, fg=fg_color)
                        self.cubematrix[idx][crow][ccol].config(bg=self._from_rgb(colorname))
                        if not self.is_use_scan_cube_label:
                            self.cubematrix[idx][crow][ccol].grid_remove()
                        else:
                            self.cubematrix[idx][crow][ccol].grid(row=crow, column=ccol, ipadx=1, ipady=2, padx=2, pady=2)

            scanimg		= {}
            try:
                scanimg	= camera.cv_images[cap_idx]
                if self.scanImageFrame[sname]['wraplength'] != 10:
                    scanimg = Image.fromarray(scanimg).resize((108,97))
                    scanout = ImageTk.PhotoImage(scanimg)
                    self.scanImageFrame[sname].configure(image=scanout)
                    self.scanImageFrame[sname].image = scanout
                    self.scanImageFrame[sname]['wraplength'] = 10
                    self.scanImageFrame[sname]['text'] = sname

            except IndexError:
                scanimg	= {}


        self.after(100, self.show_scan_cube_status)

    def __init__(self, *args, **kwargs):
        super(Solver, self).__init__(*args, **kwargs)
        
        self.channel 			= 'solver'
        self.pub 				= QueuePubSub(queues)
        self.sub 				= QueuePubSub(queues).subscribe('update')

        self.cubeScanList		= ['F', 'R', 'B', 'L', 'D', 'U']
        self.scanImageFrame		= {}
        self.cubematrix			= [[[0 for col in range(3)] for row in range(3)] for face in range(6)]

        # Grip/Stop Functions
        self.grip_labelframe = tk.LabelFrame(self, text='Grip/Stop Functions')
        self.grip_labelframe.pack(side='left', fill=tk.Y, ipadx=2, ipady=2, padx=20, pady=20)

        # Side Grip/Stop Buttons
        self.button_names = ['Fix', 'Release', 'Infinite', 'Stop', 'Cube Status']
        max_button_width = max(map(lambda x: len(x), self.button_names))
        self.buttons = {}
        for button_name in self.button_names:
            self.buttons[button_name] = tk.Button(self.grip_labelframe, text=button_name, width=max_button_width, height=1, command=lambda label=button_name: self.button_action(label))
            self.buttons[button_name].pack(side='top', expand=True)

        # Solver/Reader Functions
        self.solver_labelframe = tk.LabelFrame(self, text='Solver/Reader Functions')
        self.solver_labelframe.pack(side='top', fill=tk.BOTH, ipadx=2, ipady=2, padx=2, pady=20, expand=True)

        # Solver/Reader Buttons & Progress Bars 

        self.solver_labelframe.rowconfigure(0, weight=1)
        self.solver_labelframe.rowconfigure(1, weight=1)
        self.solver_labelframe.columnconfigure(0, weight=1)
        self.solver_labelframe.columnconfigure(1, weight=3)
        self.solver_labelframe.columnconfigure(2, weight=1)

        new_buttons = ['Read Cube', 'Solve Cube', 'Scramble Cube']
        max_button_width = max(map(lambda x: len(x), new_buttons))
        for idx, button_name in enumerate(new_buttons):
            self.buttons[button_name] = tk.Button(self.solver_labelframe, text=button_name, width=max_button_width+10, height=1, command=lambda label=button_name: self.button_action(label))
            self.buttons[button_name].grid(row=idx, column=0, padx=20, pady=0, sticky='nw')

        self.progress_bars = {}
        self.bar_names = new_buttons
        for idx, bar_name in enumerate(self.bar_names):
            self.progress_bars[bar_name] = ttk.Progressbar(self.solver_labelframe, orient='horizontal', length=480, mode='determinate')
            self.progress_bars[bar_name].grid(row=idx, column=1, padx=10, pady=7, sticky='nwe')

        self.progress_labels = {}
        self.label_names = new_buttons
        max_button_width = max(map(lambda x: len(x), self.label_names))
        for idx, label_name in enumerate(self.label_names):
            self.progress_labels[label_name] = tk.Label(self.solver_labelframe, text='0%', height=1, width=max_button_width, justify=tk.LEFT, anchor=tk.W)
            self.progress_labels[label_name].grid(row=idx, column=2, padx=20, pady=7, sticky='nw')

        self.button_names += new_buttons
        self.buttons['Solve Cube'].config(state='disabled')

        self.video_labelframe = tk.LabelFrame(self, text='video')
        self.video_labelframe.pack(side='left', fill=tk.BOTH, ipadx=0, ipady=0, padx=0, pady=0, expand=False)

        self.display1 = tk.Label(self.video_labelframe, text='video')
        self.display1.grid(row=0, column=0, padx=0, pady=0)  #Display 1


        ##############
        self.cube_labelframe = tk.LabelFrame(self, text='read cube status')
        self.cube_labelframe.pack(side='top', fill=tk.BOTH, ipadx=0, ipady=0, padx=0, pady=0, expand=True)

        self.is_use_scan_cube_label	= True
        for idx, sname in enumerate(self.cubeScanList):
            row_col = self.get_cube_row_col(sname)
            row		= row_col[0]
            col		= row_col[1]
            self.scanImageFrame[sname]	= tk.Label(self.cube_labelframe, text=sname, compound=tk.CENTER, bg="lightgray")
            self.scanImageFrame[sname].grid(row=row, column=col, padx=1, pady=1)

            if self.is_use_scan_cube_label:
                for crow in range(3):
                    for ccol in range(3):
                        self.cubematrix[idx][crow][ccol]    = tk.Label(self.scanImageFrame[sname], text=sname, width=3, compound=tk.CENTER, bd=2, bg="black")

        self.show_scan_cube_status()

        self.show_frame()
        self.scanCubeReset()
        self.after(50, self.refresh_page)

    def scanCubeReset(self):

        camera.cv_images 	= []
        scanout				= {}
        cube_image_file	= './images/cube.jpg'
        if os.path.isfile(cube_image_file):
            scanimg = cv2.imread(cube_image_file, cv2.IMREAD_COLOR)
            scanimg	= cv2.cvtColor(scanimg, cv2.COLOR_BGR2RGB)
            scanimg = Image.fromarray(scanimg).resize((108,97))
            scanout = ImageTk.PhotoImage(scanimg)

        # Map face name to capture index (capture order: F, L, B, R, U, D)
        capture_index = {'F': 0, 'L': 1, 'B': 2, 'R': 3, 'U': 4, 'D': 5}

        # Reset classification state
        self._classification_logged = False
        camera.cubeLabels = [[['' for _ in range(3)] for _ in range(3)] for _ in range(6)]

        for idx, cubename in enumerate(self.cubeScanList):
            cap_idx = capture_index.get(cubename, idx)
            if scanout:
                self.scanImageFrame[cubename].configure(image=scanout)
                self.scanImageFrame[cubename].image = scanout
                self.scanImageFrame[cubename]['text'] = cubename
                self.scanImageFrame[cubename]['wraplength'] = 20

            for crow in range(3):
                for ccol in range(3):
                    camera.cubeColors[cap_idx][crow][ccol] = webcolors.name_to_rgb("lightgray")

    def button_action(self, label):
        if label == 'Stop' or label == 'fix' or label == 'release' or label == 'scramble':
            self.scanCubeReset()
        elif label == 'Infinite':
            #
            self.scanCubeReset()
        elif label == 'Cube Status':
            if self.is_use_scan_cube_label:
                self.is_use_scan_cube_label = False
                self.buttons[label].config(bg="green")
            else:
                self.is_use_scan_cube_label = True
                self.buttons[label].config(bg="lightgray")
        
        self.pub.publish(self.channel, label)

    def refresh_page(self):
        try:
            # block or disable the solve button
            fix_state 		= 'normal'
            release_state 	= 'normal'
            infinite_state 	= 'normal'

            read_state 		= 'normal'
            solve_state 	= 'normal'
            scramble_state 	= 'normal'

            update = self.sub.get(block=False)
            if update['fix_button_locked'] is True:
                fix_state = 'disabled'
            if update['release_button_locked'] is True:
                release_state = 'disabled'
            if update['read_button_locked'] is True:
                read_state = 'disabled'
            if update['solve_button_locked'] is True:
                solve_state = 'disabled'
            if update['scramble_button_locked'] is True:
                scramble_state = 'disabled'
            if update['infinite_button_locked'] is True:
                infinite_state = 'disabled'

            if self.buttons['Fix']['state'] != fix_state:
                self.buttons['Fix'].config(state=fix_state)
            if self.buttons['Release']['state'] != release_state:
                self.buttons['Release'].config(state=release_state)
            if self.buttons['Infinite']['state'] != infinite_state:
                self.buttons['Infinite'].config(state=infinite_state)

            if self.buttons['Solve Cube']['state'] != solve_state:
                self.buttons['Solve Cube'].config(state=solve_state)
            if self.buttons['Read Cube']['state'] != read_state:
                self.buttons['Read Cube'].config(state=read_state)
            if self.buttons['Scramble Cube']['state'] != scramble_state:
                self.buttons['Scramble Cube'].config(state=scramble_state)
            
            # update both progress bars
            read_progress_bar = update['read_status']
            solve_progress_bar = update['solve_status']
            scramble_progress_bar = update['scramble_status']
            self.progress_bars['Read Cube']['value'] = read_progress_bar
            self.progress_bars['Solve Cube']['value'] = solve_progress_bar
            self.progress_bars['Scramble Cube']['value'] = scramble_progress_bar

            # update both labels of both progress bars
            self.progress_labels['Read Cube']['text'] = '{}%'.format(int(read_progress_bar))
            self.progress_labels['Solve Cube']['text'] = '{}%'.format(int(solve_progress_bar))
            self.progress_labels['Scramble Cube']['text'] = '{}%'.format(int(scramble_progress_bar))

        except Empty:
            pass
        finally:
            self.after(50, self.refresh_page)

class Camera(Page):
    def __init__(self, *args, **kwargs):
        super(Camera, self).__init__(*args, **kwargs)
        
        self.channel = 'config'
        self.pub = QueuePubSub(queues)

        # left big frame
        self.entries_frame = tk.LabelFrame(self, text='Interest Zones')
        self.entries_frame.pack(side='left', fill=tk.Y, ipadx=2, ipady=2, padx=20, pady=20)

        # configure layout of labels and buttons in the left frame
        self.entries_frame.rowconfigure(0, weight=1)
        self.entries_frame.rowconfigure(1, weight=1)
        self.entries_frame.rowconfigure(2, weight=1)
        self.entries_frame.rowconfigure(3, weight=1)
        self.entries_frame.rowconfigure(4, weight=1)
        self.entries_frame.columnconfigure(0, weight=1)
        self.entries_frame.columnconfigure(1, weight=1)

        # and setup the labels and the buttons in the left frame
        self.labels = {}
        self.entries = {}
        self.entry_values = {}
        self.label_names = ['X Offset (px)', 'Y Offset (px)', 'Size (px)', 'Pad (px)']
        max_button_width = max(map(lambda x: len(x), self.label_names))
        for idx, text in enumerate(self.label_names):
            self.labels[text] = tk.Label(self.entries_frame, text=text, height=1, width=max_button_width, justify='right', anchor=tk.W)
            self.labels[text].grid(row=idx, column=0, padx=20, pady=10)

            self.entry_values[text] = tk.IntVar()
            self.entries[text] = tk.Entry(self.entries_frame, justify='left', width=5, textvariable=self.entry_values[text])
            self.entries[text].grid(row=idx, column=1, padx=20, pady=10)

        # create the capture button
        self.button_frame = tk.Frame(self.entries_frame)
        self.button_frame.grid(row=4, column=0, columnspan=2)
        self.button_names = ['Load', 'Save', 'Preview']
        max_width = max(map(lambda x: len(x), self.button_names))
        self.buttons = {}
        for btn_name in self.button_names:
            self.buttons[btn_name] = tk.Button(self.button_frame, text=btn_name, width=max_width, command=lambda label=btn_name: self.button_action(label))
            self.buttons[btn_name].pack(side='left', expand=True, padx=2, pady=2)

        # right big frame (actually label) that includes the preview image from the camera
        self.images = tk.Label(self, text='No captured image', bd=2, relief=tk.RIDGE)
        self.images.pack(side='left', fill=tk.BOTH, ipadx=2, ipady=2, padx=20, pady=20, expand=True)

        # load the config file on app launch
        self.button_action(self.button_names[0])

    
    # every time the get preview button is pressed
    def button_action(self, label):
        if label in self.button_names[:2]:
            # load config file
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)

                # load config file into this class
                if label == self.button_names[0]:
                    for key in self.label_names:
                        val = config['camera'][key]
                        self.entry_values[key].set(val)
            except:
                logger.warning('config file can\'t be loaded because it doesn\'t exist')
                config = {}

            # save config file
            if label == self.button_names[1]:
                config['camera'] = {}
                for key in self.label_names:
                    config['camera'][key] = self.entry_values[key].get()
                try:
                    with open(config_file, 'w') as f:
                        json.dump(config, f, indent=4, sort_keys=True)
                except:
                    logger.warning('failed saving the config file')

            self.pub.publish(self.channel, config)

        # if we have to get a preview
        if label == self.button_names[2]:
            xoff = self.entry_values['X Offset (px)'].get()
            yoff = self.entry_values['Y Offset (px)'].get()
            dim = self.entry_values['Size (px)'].get()
            pad = self.entry_values['Pad (px)'].get()

            # 640x480
            img = camera.get_overlayed_processed_image(xoff, yoff, dim, pad)
            img = Image.fromarray(img).resize((376,282))
            out = ImageTk.PhotoImage(img)
            self.images.configure(image=out)
            self.images.image = out

class Arms(Page):
    def __init__(self, *args, **kwargs):
        super(Arms, self).__init__(*args, **kwargs)
        # label = tk.Label(self, text='This is page arms', bg='green', justify=tk.CENTER)
        # label.pack(side='top', fill='both', expand=True)

        self.channel_cfg = 'config'
        self.channel_play = 'arms_play'
        self.channel_solver = 'solver'
        self.pub = QueuePubSub(queues)

        self.arms = ['Arm 1', 'Arm 2', 'Arm 3', 'Arm 4']
        self.arm_labels = {}

        # just labels for the servos
        self.low_servo_labels = []
        self.high_servo_labels = []

        # integer entries for the servo limits
        self.low_servo_entries = []
        self.high_servo_entries = []
        self.low_servo_vals = []
        self.high_servo_vals = []

        # and the actual sliders for testing
        self.servo_sliders = []

        for idx, arm in enumerate(self.arms):
            self.arm_labels[arm] = tk.LabelFrame(self, text=arm)
            self.arm_labels[arm].pack(side='top', fill=tk.BOTH, expand=True, ipadx=10, ipady=2, padx=15, pady=5)
            
            for i in range(2):
                servo_idx = 2 * idx + i
                if servo_idx % 2 == 0:
                    t1 = 'Pos'
                else:
                    t1 = 'Rot'
                # low positioned labels
                self.low_servo_labels.append(tk.Label(self.arm_labels[arm], text='S{} '.format(servo_idx + 1) + 'Low ' + t1))
                self.low_servo_labels[-1].pack(side='left', fill=tk.BOTH, padx=2)
                # low positioned entries
                self.low_servo_vals.append(tk.IntVar())
                self.low_servo_entries.append(tk.Entry(self.arm_labels[arm], justify='left', width=5, textvariable=self.low_servo_vals[-1]))
                self.low_servo_entries[-1].pack(side='left', fill=tk.X, padx=2)

                # high positioned labels
                self.high_servo_labels.append(tk.Label(self.arm_labels[arm], text='S{} '.format(servo_idx + 1) + 'High ' + t1))
                self.high_servo_labels[-1].pack(side='left', fill=tk.BOTH, padx=2)
                # high positioned entries
                self.high_servo_vals.append(tk.IntVar())
                self.high_servo_entries.append(tk.Entry(self.arm_labels[arm], justify='left', width=5, textvariable=self.high_servo_vals[-1]))
                self.high_servo_entries[-1].pack(side='left', fill=tk.X, padx=2)

                # slider
                self.servo_sliders.append(tk.Scale(self.arm_labels[arm], from_=0, to=100, orient=tk.HORIZONTAL, showvalue=0, command=lambda val, s=servo_idx: self.scale(s, val)))
                self.servo_sliders[-1].pack(side='left', fill=tk.X, expand=True, padx=3)

        self.button_frame = tk.LabelFrame(self, text='Actions')
        self.button_frame.pack(side='top', fill=tk.BOTH, expand=True, ipadx=10, ipady=2, padx=15, pady=5)
        self.button_names = ['Load Config', 'Save Config', 'Random']
        max_width = max(map(lambda x: len(x), self.button_names))
        self.buttons = {}
        for btn_name in self.button_names:
            self.buttons[btn_name] = tk.Button(self.button_frame, text=btn_name, width=max_width, command=lambda label=btn_name: self.button_action(label))
            self.buttons[btn_name].pack(side='left', expand=True)
        
        # load config values on app launch
        self.button_action(self.button_names[0])

    def scale(self, servo, value):
        self.pub.publish(self.channel_play, [servo, value])

    def button_action(self, label):
        # load/save config file
        if label in self.button_names[:2]:
            # load config file
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)

                # load config file into this class
                if label == self.button_names[0]:
                    for idx, _ in enumerate(self.arms * 2):
                        arm = config['servos']['s{}'.format(idx + 1)]
                        self.low_servo_vals[idx].set(arm['low'])
                        self.high_servo_vals[idx].set(arm['high'])
            except:
                logger.warning('config file can\'t be loaded because it doesn\'t exist')
                config = {}

            # save config file
            if label == self.button_names[1]:
                config['servos'] = {}
                for idx, _ in enumerate(self.arms * 2):
                    arm = {
                        'low': self.low_servo_vals[idx].get(),
                        'high': self.high_servo_vals[idx].get()
                    }
                    config['servos']['s{}'.format(idx + 1)] = arm
                try:
                    with open(config_file, 'w') as f:
                        json.dump(config, f, indent=4, sort_keys=True)
                except:
                    logger.warning('failed saving the config file')

            self.pub.publish(self.channel_cfg, config)

        elif label == self.button_names[2]:
            self.pub.publish(self.channel_solver, label)
            

class MainView(tk.Tk):
    def __init__(self, size, name):

        # initialize root window and shit
        super(MainView, self).__init__()
        self.geometry(size)
        self.title(name)
        self.resizable(False, False)
        # initialize master-root window
        window = tk.Frame(self, bd=2)
        window.pack(side='top', fill=tk.BOTH, expand=True)
        
        # create the 2 frames within the window container
        button_navigator = tk.Frame(window, bd=2, relief=tk.FLAT)
        pages = tk.Frame(window, bd=2, relief=tk.RIDGE)

        # define the frames' dimensions
        window.rowconfigure(0, weight=19)
        window.rowconfigure(1, weight=1, minsize=25)
        window.columnconfigure(0, weight=1)

        # and organize them by rows/columns
        pages.grid(row=0, column=0, sticky='nswe', padx=2, pady=2)
        button_navigator.grid(row=1, column=0, sticky='nswe', padx=2, pady=2)

        # create the 3 pages 
        self.frames = {}
        for F in (Solver, Camera, Arms):
            page_name = F.__name__
            frame = F(pages)
            self.frames[page_name] = frame

        # and link the pages to their respective buttons
        for label in ('Solver', 'Camera', 'Arms'):
            button = tk.Button(button_navigator, text=label, command=self.frames[label].show)
            button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=3)

        # and show the default page
        self.frames['Solver'].show()

class PiCameraPhotos():
    def __init__(self, virtual=False):
        self.virtual = virtual
        self.isbusy			= False
        self.lock			= td.Lock()
        # image processing options (loaded from config at runtime)
        self.apply_clahe		= True
        self.apply_bilateral	= True
        self.enable_stability	= True
        self.enable_auto_roi		= True
        self.stability_threshold	= 0.7
        self.num_stability_samples	= 3
        if virtual:
            from virtual import VirtualCamera
            self.cam			= VirtualCamera()
            logger.info('PiCameraPhotos initialized in VIRTUAL mode')
        else:
            self.cam			= cv2.VideoCapture(0)
        self.cv_image		= np.zeros((480, 640, 3), dtype=np.uint8)
        self.cv_images		= []
        self.cubeColors 	= [[[0 for col in range(3)] for row in range(3)] for face in range(6)]
        self.cubeLabels		= [[['' for col in range(3)] for row in range(3)] for face in range(6)]

    def update_config(self, camera_config):
        """Update image processing options from config.json camera section."""
        self.apply_clahe		= camera_config.get('apply_clahe', True)
        self.apply_bilateral	= camera_config.get('apply_bilateral', True)
        self.enable_stability	= camera_config.get('enable_stability_check', True)
        self.enable_auto_roi		= camera_config.get('enable_auto_roi', True)
        self.stability_threshold	= camera_config.get('stability_threshold', 0.7)
        self.num_stability_samples	= camera_config.get('num_stability_samples', 3)
        self.use_raw_colors		= camera_config.get('use_raw_colors', True)
		
    def IsBusy(self):
        return self.isbusy

    def capture(self):
        """
        Captures an image from the camera.
        :return: A numpy array image.
        """
        with self.lock:
            self.isbusy	= True

            x			= 30
            y			= 10
            img			= self.cv_image
            if not hasattr(img, 'shape') or img.size == 0:
                self.isbusy = False
                return np.zeros((480, 640, 3), dtype=np.uint8)
            # Crop: remove 50px from bottom/right, 10px from top, 30px from left
            img 		= img[y:img.shape[0]-50, x:img.shape[1]-50]

            self.isbusy	= False

            return img

    def get_camera_roi(self, xoff, yoff, dim, pad):
        """
        Computes the Regions-of-Interest for the cube's labels.
        :param xoff: Offset in pixels on the X axis.
        :param yoff: Offset in pixels on the Y axis.
        :param dim: Dimension of the squared box that sits on top of a label. Measured in pixels.
        :param pad: Pad distance between squared boxes.
        :return: A 3x3 list with each element containing a dictionary with 'x', 'y', 'dim' labels
        representing the top left corner of a label and the dimension of that squared box.
        """
        cols_count = rows_count = 3
        roi = [[0 for x in range(cols_count)] for x in range(rows_count)]
        for row in range(rows_count):
            for col in range(cols_count):
                roi[row][col] = {
                    'x': xoff + col * (dim + pad),
                    'y': yoff + row * (dim + pad),
                    'dim': dim
                }
        return roi

    def get_processed_image(self):
        """
        Captures an image and processes it. Applies CLAHE on L channel of LAB
        for contrast enhancement, and bilateral filtering for noise reduction
        while preserving edges. Processing options are controlled by config.
        :return: RGB image as numpy array.
        """

        sleep(0.3)
        img = self.capture()
        img = np.asarray(img)

        if img.size == 0 or img.shape[0] < 10 or img.shape[1] < 10:
            return img

        if self.apply_clahe:
            lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l_channel = clahe.apply(l_channel)
            lab = cv2.merge((l_channel, a_channel, b_channel))
            img = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

        if self.apply_bilateral:
            img = cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)

        return img

    def get_raw_image(self):
        """
        Captures a raw (unprocessed) image for color extraction.
        CLAHE/bilateral processing can distort color distances (especially
        yellow/green and red/orange), so raw colors are used for classification.
        :return: RGB image as numpy array.
        """
        sleep(0.3)
        img = self.capture()
        return np.asarray(img)

    def get_overlayed_processed_image(self, xoff, yoff, dim, pad):
        """
        Captures an image, processes it and draws the Regions-of-Interest
        on the image itself.
        It needs the `xoff`, `yoff`, `dim` and `pad` arguments when calling get_camera_roi
        method.
        :return: RGB image as numpy array.
        """
        img = self.get_processed_image()
        roi = self.get_camera_roi(xoff, yoff, dim, pad)

        max_x = 0
        max_y = 0
        for rectangles in roi:
            for rectangle in rectangles:
                x = rectangle['x']
                y = rectangle['y']
                dim = rectangle['dim']
                cv2.rectangle(img, (x, y), (x+dim, y+dim), (255,255,255), thickness=2)

        return img

    @staticmethod
    def extract_color_patch(img, x, y, dim):
        region_pixels = img[y:y+dim, x:x+dim]
        if region_pixels.size == 0:
            return rgb_to_lab([0, 0, 0])
        h, w = region_pixels.shape[:2]
        y0 = int(h * 0.25)
        y1 = int(h * 0.75)
        x0 = int(w * 0.25)
        x1 = int(w * 0.75)
        core = region_pixels[y0:y1, x0:x1]
        if core.size == 0:
            core = region_pixels
        rgb_med = np.median(core.reshape(-1, 3), axis=0)
        lab_color = rgb_to_lab(rgb_med)
        return lab_color
    
    @staticmethod
    def extract_rgb_patch(img, x, y, dim):
        region_pixels = img[y:y+dim, x:x+dim]
        if region_pixels.size == 0:
            return np.array([0, 0, 0], dtype=np.float32)
        h, w = region_pixels.shape[:2]
        y0 = int(h * 0.25)
        y1 = int(h * 0.75)
        x0 = int(w * 0.25)
        x1 = int(w * 0.75)
        core = region_pixels[y0:y1, x0:x1]
        if core.size == 0:
            core = region_pixels
        rgb_med = np.median(core.reshape(-1, 3), axis=0)
        return rgb_med.astype(np.float32)

    def get_camera_color_patches(self, xoff, yoff, dim, pad, pic_counter):
        # Use raw (unprocessed) image for color extraction when enabled.
        # CLAHE/bilateral processing distorts color distances, especially
        # for yellow/green and red/orange pairs.
        if getattr(self, 'use_raw_colors', True):
            img = self.get_raw_image()
        else:
            img = self.get_processed_image()
        roi = self.get_camera_roi(xoff, yoff, dim, pad)
        color_patches = np.zeros(shape=(3, 3, 3), dtype=np.uint8)

        all_rgb_patches = []
        for row in range(3):
            for col in range(3):
                region = roi[row][col]
                x, y, dim_roi = region['x'], region['y'], region['dim']
                rgb = PiCameraPhotos.extract_rgb_patch(img, x, y, dim_roi)
                all_rgb_patches.append(rgb)
    
        if COLOR_DETECTOR_AVAILABLE and self.enable_stability:
            all_rgb_arr = np.array(all_rgb_patches, dtype=np.uint8).reshape(3, 3, 3)
            stability = StabilityChecker(num_samples=self.num_stability_samples)
            stability_score = stability.check_stability(all_rgb_arr.astype(np.float32))
            logger.debug(f'pic {pic_counter} stability score: {stability_score:.3f}')
    
        for idx, rgb in enumerate(all_rgb_patches):
            row, col = divmod(idx, 3)
            rgb_u8 = np.clip(rgb, 0, 255).astype(np.uint8)
            color_patches[row, col, :] = rgb_u8
            self.cubeColors[pic_counter][row][col] = tuple(map(int, rgb_u8))

        return color_patches

    def destructor(self):
        self.cam.release()
        cv2.destroyAllWindows()

class RubiksSolver():
    def __init__(self, channel):
        """
        Initialize a model object for the FSM.
        :param channel: The channel to which commands have to be published.
        """
        self.pub 				= QueuePubSub(queues)
        self.channel 			= channel
        self.thread_stopper 	= td.Event()
        self.thread 			= None
        self.thread2_stopper 	= td.Event()
        self.thread2 			= None
        self.cubesolution 		= None
        self.infiniteStatus		= False
        self.isFixedCube		= False

    def __execute_command(self, command):
        """
        Execute a command on the PivotPi.
        :param command: A dictionary containing the 'time', 'servo' and
        'position' keys representing the time needed for the command to get
        executed, the servo onto which the action has to be applied (starts from 1)
        and the position in degrees at which the servo has to move to.
        :return: True if it succeeded or False otherwise.
        """
        time = command['time']
        servo = int(re.search(r'\d+', command['servo']).group()) - 1
        position = command['position']

        # move the servo
        try:
            pivotpi.angle(servo, position)
            sleep(time)
        except Exception as e:
            logger.warning(f'servo command failed: {e}')
            return False

        return True

    def __instantiate_arms(self, config, mode):
        """
        Initialize the robot's arms either in released or fixed mode.
        :param config: The configuration dictionary as it comes from the GUI app.
        :param mode: 'fix' or 'release'.
        :return: A list of 4 elements with instances of the arms.Arm class.
        """
        robot_arms = []
        servos = config['servos']

        if mode == 'fix':
            pos = 'low'
        elif mode == 'release':
            pos = 'high'
        else:
            return None

        keys = list(servos.keys())
        keys.sort()

        # because there are 4 arms
        for i in range(4):
            linear_servo = keys[2 * i]
            rotational_servo = keys[2 * i + 1]
            linear_cfg = servos[linear_servo]
            rotational_cfg = servos[rotational_servo]
            robot_arms.append(
                arms.Arm(linear_servo, rotational_servo,
                         linear_cfg['low'], linear_cfg['high'],
                         rotational_cfg['low'], rotational_cfg['high'],
                         linear_cfg[pos], rotational_cfg['low'],
                         rotation_speed=0.0001, command_delay=0.00005)
            )

        return robot_arms

    def __instantiate_arms_in_release_mode(self, config):
        """
        Same thing as calling __instantiate_arms with mode set to 'release'.
        :param config: The configuration dictionary as it comes from the GUI app.
        :return: A list of 4 elements with instances of the arms.Arm class.
        """
        return self.__instantiate_arms(config, mode='release')

    def __instantiate_arms_in_fix_mode(self, config):
        """
        Same thing as calling __instantiate_arms with mode set to 'fix'.
        :param config: The configuration dictionary as it comes from the GUI app.
        :return: A list of 4 elements with instances of the arms.Arm class.
        """
        return self.__instantiate_arms(config, mode='fix')

    def __generate_handwritten_solution_from_cube_state(self, cube_centers, rubiks_labels):
        """
        Generate movement solution for the robot's arms. This method returns the sequence of
        steps required for the robot to solve the cube.

        :param cube_centers: A 6-element list containing the numeric labels for each face's center.
        :param rubiks_labels: Flattened Rubik's cube labels in the order expected by the muodov/kociemba library.
        These labels are numeric.
        :return:
        """
        # generate dictionary to map between center labels as
        # digits to labels as a handwritten notation: URFDLB
        kociembas_input_labels = {}
        for center, label in zip(cube_centers, 'U R F D L B'.split()):
            kociembas_input_labels[center] = label

        # generate the cube's state as a list of strings of 6x9 labels
        cubestate = [kociembas_input_labels[label] for label in rubiks_labels]
        cubestate = ''.join(cubestate)

        print('cubestate = ', cubestate)
        # generate the solution for the given cube's state
        solved = kociemba.solve(cubestate)
        solved = solved.split(' ')

        return solved

    def __buttons_status(self, status):
        if self.infiniteStatus:
           return True
        return status

    def unblock_solve(self, event):
        """
        Unblock the solve button in the GUI app.
        :param event: Unnecessary.
        :return: Nothing.
        """
        logger.debug('unblock solve button')
        self.pub.publish(self.channel, {
            'fix_button_locked': self.__buttons_status(False),
            'release_button_locked': self.__buttons_status(False),
            'infinite_button_locked': self.__buttons_status(False),
            'read_button_locked': self.__buttons_status(False),
            'solve_button_locked': self.__buttons_status(False),
            'scramble_button_locked': self.__buttons_status(False),
            'read_status': 0,
            'solve_status': 0,
            'scramble_status': 0
        })

    def is_finished(self, event):
        """
        Checks if any thread that runs in the background has finished (
        either for solving or reading the cube).
        :param event: Not necessary.
        :return: Whether the thread is still running or not.
        """
        if self.infiniteStatus:
            return
        return self.thread_stopper.is_set()

    def block_solve(self, event):
        """
        Blocks the solve button and stops the arms' motors.
        :param event: Not necessary here.
        :return: Nothing.
        """
        if self.infiniteStatus:
            return

        logger.debug('block solve button')
        if self.thread != None and not self.thread_stopper.is_set():
            self.thread_stopper.set()
            self.thread.join()
        hard = event.kwargs.get('hard')
        if hard is True:
            # cut the power from the servos
            logger.debug('hard stop servos')
        else:
            # just stop the motors but don't cut the power
            logger.debug('soft stop servos')
        # and publish what's necessary for the GUI
        self.pub.publish(self.channel, {
            'fix_button_locked': self.__buttons_status(False),
            'release_button_locked': self.__buttons_status(False),
            'infinite_button_locked': self.__buttons_status(False),
            'read_button_locked': self.__buttons_status(False),
            'solve_button_locked': self.__buttons_status(True),
            'scramble_button_locked': self.__buttons_status(False),
            'read_status': 0,
            'solve_status': 0,
            'scramble_status': 0
        })

    def readcube(self, event):
        """
        Spins up the thread for readcube_thread method.
        :param event: Is a dictionary that contains the arm configs as received from the GUI app.
        :return: Nothing.
        """
        logger.debug('start thread for reading the cube')
        self.config = event.kwargs.get('config')
        # update camera processing options from config
        if self.config and 'camera' in self.config:
            camera.update_config(self.config['camera'])
        self.thread_stopper.clear()
        def _safe_run():
            try:
                self.readcube_thread()
            except Exception as e:
                logger.exception(f'readcube_thread failed: {e}')
                self.cubesolution = None
            finally:
                self.thread_stopper.set()
                self.pub.publish(self.channel, {
                    'fix_button_locked': self.__buttons_status(False),
                    'release_button_locked': self.__buttons_status(False),
                    'infinite_button_locked': self.__buttons_status(False),
                    'read_button_locked': self.__buttons_status(False),
                    'solve_button_locked': self.__buttons_status(False),
                    'scramble_button_locked': self.__buttons_status(False),
                    'read_status': 100,
                    'solve_status': 0,
                    'scramble_status': 0
                })
        self.thread = td.Thread(target=_safe_run)
        self.thread.start()

    def readcube_thread(self):
        """
        Method which scans the cube's surface.
        :return: Nothing.
        """
        logger.debug('reading cube')
        self.pub.publish(self.channel, {
            'fix_button_locked': self.__buttons_status(True),
            'release_button_locked': self.__buttons_status(True),
            'infinite_button_locked': self.__buttons_status(True),
            'read_button_locked': self.__buttons_status(True),
            'solve_button_locked': self.__buttons_status(True),
            'scramble_button_locked': self.__buttons_status(True),
            'read_status': 0,
            'solve_status': 0,
            'scramble_status' : 0
        })

        # instantiate arms and reposition
        robot_arms = self.__instantiate_arms_in_release_mode(self.config)
        generator = arms.ArmSolutionGenerator(*robot_arms)
        if not self.isFixedCube:
            generator.reposition_arms(delay=0.5)
            generator.fix()

        # test solve code
        # str = 'RRDUUDUULFRRFRRDDBFFDFFDULBLDRLDBLBUFLLULLBBBFUUFBBRRD'
        # self.generator = generator
        # self.cubesolution = list( str )
        # self.thread_stopper.set()
        # return

        # F
        generator.take_capture_order()
        generator.append_command('take photo')
        generator.take_capture_reset()

        generator.rotate_cube_towards_right()

        # L
        generator.take_capture_order()
        generator.append_command('take photo')
        generator.take_capture_reset()

        generator.rotate_cube_towards_right()

        # B
        generator.take_capture_order()
        generator.append_command('take photo')
        generator.take_capture_reset()

        generator.rotate_cube_towards_right()

        # R
        generator.take_capture_order()
        generator.append_command('take photo')
        generator.take_capture_reset()

        generator.rotate_cube_towards_right()
        generator.rotate_cube_upwards()

        # U
        generator.take_capture_order()
        generator.append_command('take photo')
        generator.take_capture_reset()

        generator.rotate_cube_upwards()
        generator.rotate_cube_upwards()

        # D
        generator.take_capture_order()
        generator.append_command('take photo')
        generator.take_capture_reset()

        # goto F 
        generator.rotate_cube_upwards()

        # save the generator for solving the cube
        self.generator = generator

        # get the generated sequence
        sequence = generator.arms_solution

        # execute the generated sequence of motions
        # while at the same time capturing the photos of the cube
        numeric_faces = []
        length = len(sequence)
        pic_counter = 0
        for idx, step in enumerate(sequence):
            # quit process if it has been stopped
            if self.thread_stopper.is_set():
                return
            # take photos or rotate the bloody cube
            if step:
                logger.debug('Execute \'' + str(step) + '\'')
                if step == 'take photo':
                    xoff = self.config['camera']['X Offset (px)']
                    yoff = self.config['camera']['Y Offset (px)']
                    dim = self.config['camera']['Size (px)']
                    pad = self.config['camera']['Pad (px)']

                    if camera.virtual:
                        camera.cam.set_photo_idx(pic_counter)
                        with camera.lock:
                            camera.cv_image = camera.cam.get_rgb()

                    # enable this if you want to have the cube's pics saved
                    camera.cv_images.append( camera.get_overlayed_processed_image(xoff,yoff,dim,pad) )
                    lab_face = camera.get_camera_color_patches(xoff, yoff, dim, pad, pic_counter)
                    numeric_faces.append(lab_face)

                    pic_counter += 1
                else:
                    success = self.__execute_command(step)

            # update the progress bar
            self.pub.publish(self.channel, {
                'fix_button_locked': self.__buttons_status(True),
                'release_button_locked': self.__buttons_status(True),
                'infinite_button_locked': self.__buttons_status(True),
                'read_button_locked': self.__buttons_status(True),
                'solve_button_locked': self.__buttons_status(True),
                'scramble_button_locked': self.__buttons_status(True),
                'read_status': 100 * (idx + 1) / length,
                'solve_status': 0,
                'scramble_status' : 0
            })

        # reorder faces based on the current position of the rubik's cube
        # after it has been rotated multiple times to scan its labels
        # and also map the labels so that they match the pattern imposed
        # by muodov/kociemba's library: URFDLB
        # Capture order (from inline comments in the capture sequence above):
        #   pic 0 = F, pic 1 = L, pic 2 = B, pic 3 = R, pic 4 = U, pic 5 = D
        # Map to URFDLB: U=pic4, R=pic3, F=pic0, D=pic5, L=pic1, B=pic2
        reoriented_faces = [
            numeric_faces[4],  # U
            numeric_faces[3],  # R
            numeric_faces[0],  # F
            numeric_faces[5],  # D
            numeric_faces[1],  # L
            numeric_faces[2]   # B
        ]

        # reshape the little bastard faces to be "fittable" by the KMeans algorithm
        for i in range(6):
            reoriented_faces[i] = reoriented_faces[i].reshape((3*3, 3))

        # Option 3: runtime calibration by using the 6 center stickers as references.
        # reoriented_faces are already in the order expected by kociemba: URFDLB.
        rubiks_colors = np.concatenate(reoriented_faces, axis=0).reshape(-1, 3)
        rubiks_lab = rgb_array_to_lab(rubiks_colors)

        cube_centers_when_flat = [4, 13, 22, 31, 40, 49]
        centers_lab = rubiks_lab[cube_centers_when_flat]

        # KMeans clustering: automatically classify 54 stickers into 6 groups
        # without relying on pre-defined reference colors.
        cluster_centers_lab, cluster_labels = cluster_colors(rubiks_lab, n_colors=6)

        # Map each cluster to a face (URFDLB) using the center stickers.
        # Each center sticker belongs to a known face, so the cluster it falls
        # into tells us which face that cluster represents.
        cluster_to_face = {}
        for face_idx, center_idx in enumerate(cube_centers_when_flat):
            cluster_id = cluster_labels[center_idx]
            cluster_to_face[cluster_id] = face_idx

        # Build distance matrix (used by both methods and correction algorithm)
        d = distance.cdist(rubiks_lab, centers_lab, metric='euclidean')

        # Use KMeans if all 6 centers are in distinct clusters AND the result
        # is reasonably balanced (each color 9 stickers). Otherwise fall back
        # to center-based distance classification.
        use_kmeans = len(cluster_to_face) == 6
        if use_kmeans:
            rubiks_labels = np.array([cluster_to_face[c] for c in cluster_labels], dtype=int)
            for i, ci in enumerate(cube_centers_when_flat):
                rubiks_labels[ci] = i
            kmeans_counts = Counter(rubiks_labels)
            # Check if KMeans result is balanced (each color has 9 stickers)
            if len(kmeans_counts) != 6 or set(kmeans_counts.values()) != {9}:
                # KMeans unbalanced - check if it's worse than center-based
                center_labels = np.argmin(d, axis=1).astype(int)
                for i, ci in enumerate(cube_centers_when_flat):
                    center_labels[ci] = i
                center_counts = Counter(center_labels)
                kmeans_imbalance = sum(abs(v - 9) for v in kmeans_counts.values())
                center_imbalance = sum(abs(v - 9) for v in center_counts.values())
                if center_imbalance <= kmeans_imbalance:
                    logger.info(f'KMeans unbalanced (imbalance={kmeans_imbalance}), '
                              f'using center-based (imbalance={center_imbalance})')
                    rubiks_labels = center_labels
                else:
                    logger.info(f'KMeans classification: {dict(kmeans_counts)}')
            else:
                logger.info(f'KMeans classification: {dict(kmeans_counts)}')
        else:
            logger.warning(f'KMeans: only {len(cluster_to_face)} clusters have centers, '
                          f'falling back to center-based distance')
            rubiks_labels = np.argmin(d, axis=1).astype(int)
            for i, ci in enumerate(cube_centers_when_flat):
                rubiks_labels[ci] = i

        if COLOR_DETECTOR_AVAILABLE:
            face_colors_3x3x3 = rubiks_colors.reshape(6, 3, 3, 3)
            centers_rgb = face_colors_3x3x3[:, 1, 1, :]
            for face_idx in range(6):
                face_rgb = face_colors_3x3x3[face_idx]
                matched = ColorMatcher.match_sticker_colors(face_rgb, centers_rgb)
                corrected = ColorMatcher.improve_color_consistency(face_rgb, matched)
                face_colors_3x3x3[face_idx] = corrected
            rubiks_colors = face_colors_3x3x3.reshape(-1, 3)
            rubiks_lab = rgb_array_to_lab(rubiks_colors)
            d = distance.cdist(rubiks_lab, centers_lab, metric='euclidean')
            rubiks_labels = np.argmin(d, axis=1).astype(int)
            for i, ci in enumerate(cube_centers_when_flat):
                rubiks_labels[ci] = i

        # Correct color misclassifications using cube validity constraints.
        # This fixes common issues like red/orange confusion where the center
        # sticker color doesn't represent the color of stickers on other faces
        # due to lighting variation.
        rubiks_labels = correct_color_classification(rubiks_labels, d, cube_centers_when_flat)

        # Store classification labels for UI display.
        # rubiks_labels is in URFDLB order (0=U,1=R,2=F,3=D,4=L,5=B), 54 stickers.
        # Convert to capture order (F,L,B,R,U,D) for UI access.
        urfdlb_to_capture = {0: 4, 1: 3, 2: 0, 3: 5, 4: 1, 5: 2}  # URFDLB idx -> capture idx
        kociemba_letters = {0: 'U', 1: 'R', 2: 'F', 3: 'D', 4: 'L', 5: 'B'}
        camera.cubeLabels = [['' for _ in range(3)] for _ in range(3) for _ in range(6)]
        camera.cubeLabels = [[['' for _ in range(3)] for _ in range(3)] for _ in range(6)]
        for flat_idx in range(54):
            urfdlb_face = flat_idx // 9
            sticker = flat_idx % 9
            r, c = divmod(sticker, 3)
            cap_idx = urfdlb_to_capture[urfdlb_face]
            camera.cubeLabels[cap_idx][r][c] = kociemba_letters[rubiks_labels[flat_idx]]

        logger.info(f'cubeLabels filled: F={camera.cubeLabels[0][1][1]}, '
                    f'L={camera.cubeLabels[1][1][1]}, B={camera.cubeLabels[2][1][1]}, '
                    f'R={camera.cubeLabels[3][1][1]}, U={camera.cubeLabels[4][1][1]}, '
                    f'D={camera.cubeLabels[5][1][1]}')

        cube_centers = list(range(6))
        labels_of_each_color = dict(Counter(rubiks_labels))

        # calculate how many different colors there are on each face
        # required for detecting if the cube is already solved
        face_color_labels = [list(set(rubiks_labels[i * 9: (i + 1) * 9])) for i in range(6)]
        face_labels_count = [len(x) for x in face_color_labels]

        # check if each center has a different label
        if len(set(cube_centers)) != 6:
            self.cubesolution = None
            logger.warning('didn\'t find the 6 cube centers of the rubik\'s cube. Cube centers are {}'.format(cube_centers))
            # logger.debug(rubiks_labels.reshape((6,3,3)))

        # check if there's an equal number of labels for each color of all six of them
        elif len(set(labels_of_each_color.values())) != 1:
            self.cubesolution = None
            logger.warning('found a different number of labels for some centers off the cube. The number of labels that were detected are {}'.format(labels_of_each_color))
            # logger.debug(rubiks_labels.reshape((6,3,3)))

        # check if the cube is already solved
        elif len(set(face_labels_count)) == 1:
            self.cubesolution = []
            logger.warning('the cube is already solved')

        # if all tests from the above are a go then go and solve the cube
        else:
            self.cubesolution = self.__generate_handwritten_solution_from_cube_state(cube_centers, rubiks_labels)
            logger.info(f'cube solution: {self.cubesolution}')

        # mark the end of the thread
        self.thread_stopper.set()

        # if the cube is already solved, then
        # bring the FSM into its rest state
        if self.cubesolution == []:
            self.stop(hard=False)

        self.pub.publish(self.channel, {
            'fix_button_locked': self.__buttons_status(False),
            'release_button_locked': self.__buttons_status(False),
            'infinite_button_locked': self.__buttons_status(False),
            'read_button_locked': self.__buttons_status(False),
            'solve_button_locked': self.__buttons_status(False),
            'scramble_button_locked': self.__buttons_status(False),
            'read_status': 100,
            'solve_status': 0,
            'scramble_status' : 0
        })

    def solvecube(self, event):
        """
        Spins up the thread for solvecube_thread method.
        :param event: Not necessary.
        :return: Nothing.
        """
        logger.debug('start thread for solving the cube')
        self.thread_stopper.clear()
        def _safe_run():
            try:
                self.solvecube_thread()
            except Exception as e:
                logger.exception(f'solvecube_thread failed: {e}')
            finally:
                self.thread_stopper.set()
                self.pub.publish(self.channel, {
                    'fix_button_locked': self.__buttons_status(False),
                    'release_button_locked': self.__buttons_status(False),
                    'infinite_button_locked': self.__buttons_status(False),
                    'read_button_locked': self.__buttons_status(False),
                    'solve_button_locked': self.__buttons_status(False),
                    'scramble_button_locked': self.__buttons_status(False),
                    'read_status': 0,
                    'solve_status': 0,
                    'scramble_status': 0
                })
        self.thread = td.Thread(target=_safe_run)
        self.thread.start()

    def solvecube_thread(self):
        """
        Solve's the Rubik's cube. Uses the cubesolution attribute
        to get its steps.
        :return: Nothing.
        """
        logger.debug('solving cube')
        self.pub.publish(self.channel, {
            'fix_button_locked': self.__buttons_status(True),
            'release_button_locked': self.__buttons_status(True),
            'infinite_button_locked': self.__buttons_status(True),
            'read_button_locked': self.__buttons_status(True),
            'solve_button_locked': self.__buttons_status(True),
            'scramble_button_locked': self.__buttons_status(True),
            'read_status': 100,
            'solve_status': 0,
            'scramble_status': 0
        })

        # stop this thread if there's no solution
        if not self.cubesolution:
            self.infiniteStatus = False
            self.thread_stopper.set()
            self.thread2_stopper.set()
            return

        # otherwise instantiate the arms and reposition (and eventually solve the cube)
        # robot_arms = self.__instantiate_arms_in_fix_mode(self.config)
        # generator = arms.ArmSolutionGenerator(*robot_arms)
        generator = self.generator
        generator.reset_arm_solution()
        generator.solution(self.cubesolution)

        # get the generated sequence
        sequence = generator.arms_solution

        # solve the rubik's cube by actuating the arms
        length = len(sequence)
        for idx, step in enumerate(sequence):
            if self.thread_stopper.is_set():
                return
            if step:
                logger.debug('Execute \'' + str(step) + '\'')
                success = self.__execute_command(step)
            self.pub.publish(self.channel, {
                'fix_button_locked': self.__buttons_status(True),
                'release_button_locked': self.__buttons_status(True),
                'infinite_button_locked': self.__buttons_status(True),
                'read_button_locked': self.__buttons_status(True),
                'solve_button_locked': self.__buttons_status(True),
                'scramble_button_locked': self.__buttons_status(True),
                'read_status': 100,
                'scramble_status': 0,
                'solve_status': 100 * (idx + 1) / length
            })

        self.thread_stopper.set()
        self.pub.publish(self.channel, {
            'fix_button_locked': self.__buttons_status(False),
            'release_button_locked': self.__buttons_status(False),
            'infinite_button_locked': self.__buttons_status(False),
            'read_button_locked': self.__buttons_status(False),
            'solve_button_locked': self.__buttons_status(True),
            'scramble_button_locked': self.__buttons_status(False),
            'read_status': 0,
            'solve_status': 0,
            'scramble_status' : 0
        })

    def scramble_str(self, scramble_length):
        moves = ["R", "R'", "R2", "L", "L'", "L2", "U", "U'", "U2", "D", "D'", "D2", "F", "F'", "F2", "B", "B'", "B2"]

        scramble = ""
        for i in range(0, scramble_length):
            random_move = random.randint(0, len(moves) - 1)
            if i > 0:
                while moves[random_move][0] == prev_move[0]:
                    random_move = random.randint(0, len(moves) - 1)

            scramble += " " + moves[random_move]
            prev_move = moves[random_move]

        return scramble.strip().split(' ')

    def scramblecube(self, event):
        """
        Spins up the thread for scramblecube_thread method.
        :param event: Not necessary.
        :return: Nothing.
        """
        logger.debug('start thread for scramble the cube')
        self.config = event.kwargs.get('config')
        self.thread_stopper.clear()
        def _safe_run():
            try:
                self.scramblecube_thread()
            except Exception as e:
                logger.exception(f'scramblecube_thread failed: {e}')
            finally:
                self.thread_stopper.set()
                self.pub.publish(self.channel, {
                    'fix_button_locked': self.__buttons_status(False),
                    'release_button_locked': self.__buttons_status(False),
                    'infinite_button_locked': self.__buttons_status(False),
                    'read_button_locked': self.__buttons_status(False),
                    'solve_button_locked': self.__buttons_status(False),
                    'scramble_button_locked': self.__buttons_status(False),
                    'read_status': 0,
                    'solve_status': 0,
                    'scramble_status': 100
                })
        self.thread = td.Thread(target=_safe_run)
        self.thread.start()

    def scramblecube_thread(self):
        """
        Solve's the Rubik's cube. Uses the cubesolution attribute
        to get its steps.
        :return: Nothing.
        """
        logger.debug('scramble cube')
        self.pub.publish(self.channel, {
            'fix_button_locked': self.__buttons_status(True),
            'release_button_locked': self.__buttons_status(True),
            'infinite_button_locked': self.__buttons_status(True),
            'read_button_locked': self.__buttons_status(True),
            'solve_button_locked': self.__buttons_status(True),
            'scramble_button_locked': self.__buttons_status(True),
            'read_status': 0,
            'solve_status': 0,
            'scramble_status' : 0
        })

        robot_arms = self.__instantiate_arms_in_fix_mode(self.config)
        generator = arms.ArmSolutionGenerator(*robot_arms)
        if not self.isFixedCube:
            generator.reposition_arms(delay=0.5)
            generator.fix()

        # stop this thread if there's no solution
        self.cubesolution	= self.scramble_str( random.randint(10,15) ) 
        if not self.cubesolution:
            self.thread_stopper.set()
            return

        # otherwise instantiate the arms and reposition (and eventually solve the cube)
        # generator.reset_arm_solution()
        generator.solution(self.cubesolution)

        # get the generated sequence
        sequence = generator.arms_solution

        # solve the rubik's cube by actuating the arms
        length = len(sequence)
        for idx, step in enumerate(sequence):
            if self.thread_stopper.is_set():
                return
            if step:
                logger.debug('Execute \'' + str(step) + '\'')
                success = self.__execute_command(step)
            self.pub.publish(self.channel, {
                'fix_button_locked': self.__buttons_status(True),
                'release_button_locked': self.__buttons_status(True),
                'infinite_button_locked': self.__buttons_status(True),
                'read_button_locked': self.__buttons_status(True),
                'solve_button_locked': self.__buttons_status(True),
                'scramble_button_locked': self.__buttons_status(True),
                'read_status': 0,
                'solve_status': 0,
                'scramble_status':  100 * (idx + 1) / length
            })

        self.thread_stopper.set()
        self.pub.publish(self.channel, {
            'fix_button_locked': self.__buttons_status(False),
            'release_button_locked': self.__buttons_status(False),
            'infinite_button_locked': self.__buttons_status(False),
            'read_button_locked': self.__buttons_status(False),
            'solve_button_locked': self.__buttons_status(True),
            'scramble_button_locked': self.__buttons_status(False),
            'read_status': 0,
            'solve_status': 0,
            'scramble_status' : 100
        })

    def infinitecube(self, event):
        logger.debug('start thread for infinite the cube')
        self.thread_stopper.clear()
        sleep(0.5)
        self.thread2_stopper.clear()
        self.thread2 = td.Thread(target=self.infinitecube_thread2, args=(event,))
        self.thread2.start()

    def infinitecube_thread2(self, event):

        loopIdx	= 1 
        config 	= event.kwargs.get('config')
        while self.infiniteStatus:

            self.scramblecube(event)
            self.thread.join(timeout=120)
            if self.thread.is_alive():
                logger.warning('scramblecube thread timed out')
                break
            sleep(1.5)
            if not self.infiniteStatus:
               break

            self.readcube(event)
            self.thread.join(timeout=120)
            if self.thread.is_alive():
                logger.warning('readcube thread timed out')
                break
            sleep(1.5)
            if not self.infiniteStatus:
               break

            self.solvecube(event)
            self.thread.join(timeout=300)
            if self.thread.is_alive():
                logger.warning('solvecube thread timed out')
                break
            sleep(3)
            if not self.infiniteStatus:
               break

            print("complete : loopIdx = ", loopIdx)
            loopIdx = loopIdx + 1

        self.thread2_stopper.set()

    def process_command(self, event):
        """
        Process the commands for reflexive transitions into the rest state.
        :param event: Must have 'config' and 'type' keys. Can have 'action',
        'servo' and 'pos' keys.
        :return: Nothing.
        """
        config = event.kwargs.get('config')
        cmd_type = event.kwargs.get('type')
        if cmd_type == 'system':
            action = event.kwargs.get('action')

            # instantiate arms and reposition
            robot_arms = self.__instantiate_arms_in_release_mode(config)
            generator = arms.ArmSolutionGenerator(*robot_arms)

            if action == 'fix':
                generator.fix()
            elif action == 'release':
                generator.release()
                generator.reposition_arms(delay=0.5)
            elif action == 'stop':
                generator.release()
                generator.reposition_arms(delay=0.5)

            sequence = generator.arms_solution
            for step in sequence:
                if step:
                    logger.debug(step)
                    success = self.__execute_command(step)

        elif cmd_type == 'servo':
            servo = int(event.kwargs.get('servo'))
            pos_percent = int(event.kwargs.get('pos'))
            servo_name = 's{}'.format(servo + 1)
            low = config['servos'][servo_name]['low']
            high = config['servos'][servo_name]['high']
            pos = low + (high - low) * pos_percent / 100
            pivotpi.angle(servo, pos)
            

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Rubik\'s Cube Solver Robot')
    parser.add_argument('--virtual', action='store_true', help='Run in virtual mode without hardware')
    args = parser.parse_args()

    hldr = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter('%(asctime)s %(levelname)2s %(name)s | %(message)s')
    #hldr.setLevel(logging.DEBUG)
    hldr.setLevel(logging.INFO)
    hldr.setFormatter(fmt)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(hldr)

    logger_trans = logging.getLogger('transitions')
    logger_trans.setLevel(logging.INFO)
    logger_trans.addHandler(hldr)

    queues 		= {}
    config_file = os.environ.get('WP_RUBIKS_CONFIG', 'config.json')

    # Load config to check for virtual mode (config can override --virtual flag)
    virtual_mode = args.virtual
    try:
        with open(config_file, 'r') as f:
            cfg = json.load(f)
        if cfg.get('virtual', False):
            virtual_mode = True
    except Exception as e:
        logger.warning(f'Could not load config file {config_file}: {e}')

    camera 		= PiCameraPhotos(virtual=virtual_mode)
    stop_event 	= td.Event()

    pivotpi = pp.PivotPi(virtual=virtual_mode)


    def fsm_runner():
        # sub/pub channels in and from the GUI app
        subs_channels = ['solver', 'config', 'arms_play']
        pubs_channels = ['update']
        subs = [QueuePubSub(queues).subscribe(channel) for channel in subs_channels]

        # config for arms
        config = {}
        
        # finite state machine 
        rubiks = RubiksSolver(pubs_channels[0])
        machine = transitions.Machine(
            model=rubiks,
            states=['rest', 'reading', 'solving', 'scrambling'],
            initial='rest',
            send_event=True
        )
        # FSM's transitions
        machine.add_transition(trigger='read', source='*', dest='reading', after='readcube')
        machine.on_enter_reading('unblock_solve')
        machine.add_transition(trigger='solve', source='reading', dest='solving', conditions='is_finished', after='solvecube')
        machine.add_transition(trigger='success', source='solving', dest='rest', conditions='is_finished', after='block_solve')
        machine.add_transition(trigger='scramble', source='*', dest='rest', after='scramblecube')
        machine.add_transition(trigger='infinite', source='*', dest='rest', after='infinitecube')
        machine.add_transition(trigger='stop', source='*', dest='rest', after='block_solve')
        machine.add_transition(trigger='command', source='rest', dest='=', after='process_command')

        while not stop_event.is_set():
            for sub, channel in zip(subs, subs_channels):
                try:
                    message = sub.get(block=False)
                    if channel == 'config':
                        if rubiks.state == 'rest':
                            config = message
                            logger.info('save/load button pressed (update solver configs)')
                        else:
                            logger.info('save/load button pressed, but not updating the solver configs because it\'s in rest state')
                    elif channel == 'solver':
                        msg = message.lower()
                        if 'read cube' == msg:
                            rubiks.read(config=config) # change state here
                        elif 'solve cube' == msg:
                            rubiks.solve() # change state here
                        elif 'stop' == msg:
                            rubiks.infiniteStatus 	= False
                            rubiks.isFixedCube		= False
                            rubiks.thread2_stopper.set()
                            rubiks.stop(hard=False)
                            rubiks.command(config=config, type='system', action='stop')
                            rubiks.stop(hard=True)
                        elif 'scramble cube' == msg:
                            rubiks.scramble(config=config) # change state here
                        elif 'fix' == msg:
                            rubiks.isFixedCube	= True
                            rubiks.command(config=config, type='system', action='fix') # reflexive state here
                        elif 'release' == msg:
                            rubiks.isFixedCube	= False
                            rubiks.command(config=config, type='system', action='release') # reflexive state here
                        elif 'infinite' == msg:
                            rubiks.infiniteStatus	= True
                            rubiks.infinite(config=config)
                            
                        logger.info('\'' + msg + '\' button pressed')
                    elif channel == 'arms_play':
                        servo, pos = message
                        rubiks.command(config=config, type='servo', servo=servo, pos=pos) # change state here
                        logger.info('rotate servo {} to position {}'.format(servo, pos))

                except Empty:
                    pass
                except transitions.MachineError as error:
                    logger.warning(error)

                # transition to rest from the solving state if the cube got solved
                if rubiks.state == 'solving' and rubiks.is_finished(None):
                    rubiks.success()
                    if not rubiks.infiniteStatus:
                        rubiks.command( config=config, type='system', action='release') # reflexive state here
                    logger.info('the rubik\'s cube got solved')

            sleep(0.001)
    
    fsm_thread = td.Thread(target=fsm_runner, name='FSM Runner')
    fsm_thread.start()

    mode_label = 'VIRTUAL' if virtual_mode else 'HARDWARE'
    logger.info(f'=== Starting Rubik\'s Cube Solver in {mode_label} mode ===')

    try:
        app = MainView(size='800x480', name=f'WASAMD - Rubik\'s Cube Solver [{mode_label}]')
        app.mainloop()
    except Exception as e:
        logger.exception(e)
    finally:
        camera.destructor()
        stop_event.set()
