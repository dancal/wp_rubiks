"""
Virtual hardware simulation module for testing without physical devices.
Provides VirtualController (servo) and VirtualCamera (camera) classes
that mirror the interfaces of maestro.Controller and cv2.VideoCapture.
"""

import logging
import os
import time
import numpy as np
import cv2

logger = logging.getLogger(__name__)


class VirtualController:
    """
    Virtual Maestro servo controller.
    Same interface as maestro.Controller but logs commands instead of sending them.
    """

    def __init__(self, *args, **kwargs):
        self.Targets = [0] * 24
        self.Mins = [0] * 24
        self.Maxs = [0] * 24
        self._speed = [0] * 24
        self._accel = [0] * 24
        logger.info('Virtual Maestro controller initialized')

    def close(self):
        logger.info('Virtual Maestro controller closed')

    def sendCmd(self, cmd):
        pass

    def setRange(self, chan, min_val, max_val):
        self.Mins[chan] = min_val
        self.Maxs[chan] = max_val
        logger.debug(f'Virtual setRange: chan={chan} min={min_val} max={max_val}')

    def getMin(self, chan):
        return self.Mins[chan]

    def getMax(self, chan):
        return self.Maxs[chan]

    def wait_until_at_target(self):
        time.sleep(0.01)

    def setTarget(self, chan, target):
        if self.Mins[chan] > 0 and target < self.Mins[chan]:
            target = self.Mins[chan]
        if self.Maxs[chan] > 0 and target > self.Maxs[chan]:
            target = self.Maxs[chan]
        self.Targets[chan] = target
        logger.debug(f'Virtual setTarget: chan={chan} target={target}')

    def set_target(self, chan, target, wait=True):
        self.setTarget(chan, target)

    def setSpeed(self, chan, speed):
        self._speed[chan] = speed
        logger.debug(f'Virtual setSpeed: chan={chan} speed={speed}')

    def set_speed(self, chan, speed):
        self.setSpeed(chan, speed)

    def setAccel(self, chan, accel):
        self._accel[chan] = accel
        logger.debug(f'Virtual setAccel: chan={chan} accel={accel}')

    def set_acceleration(self, chan, accel):
        self.setAccel(chan, accel)

    def getPosition(self, chan):
        return self.Targets[chan]

    def get_position(self, chan):
        return self.Targets[chan]

    def isMoving(self, chan):
        return False

    def getMovingState(self):
        return False

    def runScriptSub(self, subNumber):
        logger.debug(f'Virtual runScriptSub: sub={subNumber}')

    def stopScript(self):
        logger.debug('Virtual stopScript')


class VirtualCamera:
    """
    Virtual camera that returns pre-loaded cube face images.
    Mimics cv2.VideoCapture interface.
    """

    # Capture order matches readcube_thread inline comments:
    # F (initial), L (after 1 right), B (after 2 rights), R (after 3 rights),
    # U (after 3 rights + 1 up), D (after 3 rights + 3 ups)
    FACE_ORDER = ['F', 'L', 'B', 'R', 'U', 'D']

    def __init__(self, image_dir=None):
        if image_dir is None:
            # Allow override via environment variable
            env_dir = os.environ.get('WP_RUBIKS_IMAGE_DIR')
            if env_dir:
                image_dir = env_dir
            else:
                # Default: tests/images/back1 (sample cube images)
                base = os.path.dirname(os.path.abspath(__file__))
                image_dir = os.path.join(base, 'tests', 'images', 'back1')

        self.face_images_bgr = {}
        self.face_images_rgb = {}
        self.current_idx = 0

        for face in self.FACE_ORDER:
            path = os.path.join(image_dir, f'rubiks-side-{face}.png')
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is not None:
                self.face_images_bgr[face] = img
                self.face_images_rgb[face] = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                logger.info(f'Virtual camera loaded face {face} from {path} ({img.shape})')
            else:
                placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                self.face_images_bgr[face] = placeholder
                self.face_images_rgb[face] = placeholder.copy()
                logger.warning(f'Virtual camera: could not load {path}, using placeholder')

        if not self.face_images_bgr:
            logger.error('Virtual camera: no face images found!')

    def read(self):
        face = self.FACE_ORDER[self.current_idx % len(self.FACE_ORDER)]
        img = self.face_images_bgr.get(face, np.zeros((480, 640, 3), dtype=np.uint8))
        return True, img

    def get_rgb(self):
        face = self.FACE_ORDER[self.current_idx % len(self.FACE_ORDER)]
        return self.face_images_rgb.get(face, np.zeros((480, 640, 3), dtype=np.uint8))

    def set_photo_idx(self, idx):
        self.current_idx = idx % len(self.FACE_ORDER)
        logger.debug(f'Virtual camera set to face {self.FACE_ORDER[self.current_idx]} (idx={idx})')

    def release(self):
        logger.info('Virtual camera released')

    def set(self, prop, val):
        pass

    def get(self, prop):
        return 0
