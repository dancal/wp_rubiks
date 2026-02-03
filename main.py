from tkinter import ttk
from queue import Queue
from queue import Empty
from time import sleep
from PIL import ImageTk, Image, ImageDraw
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
                #frame 			= cv2.flip(frame, 1)
                camera.cv_image	= cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) 
                img				= Image.fromarray(camera.cv_image).resize((v_width,v_height))
                imgtk 			= ImageTk.PhotoImage(image=img)
                self.display1.imgtk = imgtk #Shows frame for display 1
                self.display1.configure(image=imgtk)
                self.after(30, self.show_frame)
            else:
                self.after(10, self.show_frame)
        
    def show_scan_cube_status(self):

        for idx, sname in enumerate(self.cubeScanList):
            for crow in range(3):
                for ccol in range(3):
                    if camera.cubeColors[idx][crow][ccol]:
                        rgb = camera.cubeColors[idx][crow][ccol]
                        r   = rgb[0]
                        g   = rgb[1]
                        b   = rgb[2]

                        colorname = webcolors.rgb_percent_to_rgb(webcolors.rgb_to_rgb_percent(rgb))
                        if crow == 1 and ccol == 1:
                            self.cubematrix[idx][crow][ccol].config(text=sname)
                        self.cubematrix[idx][crow][ccol].config(bg=self._from_rgb(colorname))
                        if not self.is_use_scan_cube_label:
                            self.cubematrix[idx][crow][ccol].grid_remove()
                        else:
                            self.cubematrix[idx][crow][ccol].grid(row=crow, column=ccol, ipadx=1, ipady=2, padx=2, pady=2)

            scanimg		= {}
            try:
                scanimg	= camera.cv_images[idx]
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

        for idx, cubename in enumerate(self.cubeScanList):
            if scanout:
                self.scanImageFrame[cubename].configure(image=scanout)
                self.scanImageFrame[cubename].image = scanout
                self.scanImageFrame[cubename]['text'] = cubename
                self.scanImageFrame[cubename]['wraplength'] = 20

            for crow in range(3):
                for ccol in range(3):
                    camera.cubeColors[idx][crow][ccol] = webcolors.name_to_rgb("lightgray")

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
    def __init__(self):
        # initialize camera with a set of predefined values
        """
        # self.camera = picamera.PiCamera()
        # self.camera.resolution = (1920, 1080)
        # self.camera.framerate = 30
        # self.camera.sensor_mode = 1
        # self.camera.rotation = 180
        # self.camera.shutter_speed = 32000
        # self.camera.brightness = 60
        # self.camera.exposure_mode = 'off'
        # self.camera.rotation = 180
        # self.camera.awb_mode = 'off'
        # self.camera.awb_gains = 1.63
        # also initialize the container for the image
        # self.stream = io.BytesIO() 
        """

        self.isbusy			= False 
        self.cam			= cv2.VideoCapture(0)
        self.cv_image		= {}
        self.cv_images		= []
        # self.cam.set(3, 640)
        # self.cam.set(4, 480)
        self.cubeColors 	= [[[0 for col in range(3)] for row in range(3)] for face in range(6)]
		
    def IsBusy(self):
        return self.isbusy

    def capture(self):
        """
        Captures an image from the Pi Camera.
        :return: A Pillow.Image image.
        """
        self.isbusy	= True

        x			= 30
        y			= 10
        img			= self.cv_image;
        h 			= img.shape[0] - 50
        w 			= img.shape[1] - 50
        img 		= img[y:y+h, x:x+w]

        #img 		= cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        #img 		= cv2.bilateralFilter(img, 9, 75, 75)
        #img 		= cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

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
        Captures an image and processes it. It applies the CLAHE algorithm,
        a Gaussian blur and an increase of the image's saturation by a fixed amount.
        :return: RGB image as numpy array.
        """

        # convert the captured image to a numpy array
        sleep(0.3)
        img = self.capture()
        img = np.asarray(img)

        return img

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
        img = self.get_processed_image()
        roi = self.get_camera_roi(xoff, yoff, dim, pad)
        color_patches = np.zeros(shape=(3, 3, 3), dtype=np.uint8)
    
        all_rgb_patches = []
        for row in range(3):
            for col in range(3):
                region = roi[row][col]
                x, y, dim = region['x'], region['y'], region['dim']
                rgb = PiCameraPhotos.extract_rgb_patch(img, x, y, dim)
                all_rgb_patches.append(rgb)
    
        # K-Means 클러스터링
        # cluster_centers, labels = cluster_colors(np.array(all_rgb_patches), n_colors=6)
        
        # 색상 매핑
        # matched_colors = match_colors(cluster_centers, REFERENCE_COLORS)
        
        # 결과 매핑
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
        # we know the servo number is the 2nd element of the string
        servo = int(command['servo'][1]) - 1
        position = command['position']

        # move the servo
        try:
            pivotpi.angle(servo, position)
            sleep(time)
        except:
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
        self.thread_stopper.clear()
        self.thread = td.Thread(target=self.readcube_thread)
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
        #reoriented_faces = [
        #    np.rot90(numeric_faces[1], k=2),  # rotate by 180 degrees
        #    np.rot90(numeric_faces[0], k=1, axes=(0, 1)),  # rotate by 90 degrees anticlockwise
        #    numeric_faces[5], # keep the same orientation
        #    numeric_faces[3], # keep the same orientation
        #    np.rot90(numeric_faces[2], k=1, axes=(1, 0)),  # rotate by 90 degrees clockwise
        #    np.rot90(numeric_faces[4], k=2)  # rotate by 180 degrees
        #]
        # F = 0, R = 1, B = 2, L = 3, U = 5, D = 4
        reoriented_faces = [
            numeric_faces[5],
            numeric_faces[1],
            numeric_faces[0],
            numeric_faces[4],
            numeric_faces[3],
            numeric_faces[2]
        ]

        # reshape the little bastard faces to be "fittable" by the KMeans algorithm
        for i in range(6):
            reoriented_faces[i] = reoriented_faces[i].reshape((3*3, 3))

        # Option 3: runtime calibration by using the 6 center stickers as references.
        # reoriented_faces are already in the order expected by kociemba: URFDLB.
        rubiks_colors = np.concatenate(reoriented_faces, axis=0).reshape(-1, 3)
        rubiks_lab = rgb_array_to_lab(rubiks_colors)

        # cube centers when flattened (URFDLB order)
        center_indexes = [4, 13, 22, 31, 40, 49]
        centers_lab = rubiks_lab[center_indexes]

        # classify each sticker by nearest center in LAB space
        d = distance.cdist(rubiks_lab, centers_lab, metric='euclidean')
        rubiks_labels = np.argmin(d, axis=1).astype(int)

        # ensure centers are unique labels 0..5
        for i, ci in enumerate(center_indexes):
            rubiks_labels[ci] = i

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
            logger.debug(self.cubesolution)

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
        self.thread = td.Thread(target=self.solvecube_thread)
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
            idx += 1

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

        return list(scramble.strip())

    def scramblecube(self, event):
        """
        Spins up the thread for solvecube_thread method.
        :param event: Not necessary.
        :return: Nothing.
        """
        logger.debug('start thread for scramble the cube')
        self.config = event.kwargs.get('config')
        self.thread_stopper.clear()
        self.thread = td.Thread(target=self.scramblecube_thread)
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
            idx += 1

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
            self.thread.join()
            sleep(1.5)
            if not self.infiniteStatus:
               break

            self.readcube(event)
            self.thread.join()
            sleep(1.5)
            if not self.infiniteStatus:
               break

            self.solvecube(event)
            self.thread.join()
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
    config_file = 'config.json'
    camera 		= PiCameraPhotos()
    stop_event 	= td.Event()

    pivotpi = pp.PivotPi()


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

    try:
        app = MainView(size='800x480', name='WASAMD - Rubik\'s Cube Solver')
        app.mainloop()
    except Exception as e:
        logger.exception(e)
    finally:
        stop_event.set()
