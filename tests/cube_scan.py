#!/usr/bin/python 

import os
import sys
import cv2
import time
from rubikscubetracker import RubiksImage, merge_two_dicts
from rubikscolorresolver import RubiksColorSolverGeneric
import json
import kociemba
import numpy as np

def CubeScan():

	#data = json.loads(str)
	data = {}
	for (side_index, side_name) in enumerate(('U', 'L', 'F', 'R', 'B', 'D')):
		filename = os.path.join(os.getcwd(), "images", "rubiks-side-%s.png" % side_name)
		rimg = RubiksImage(side_index, side_name)
		rimg.analyze_file(filename)
		data = merge_two_dicts(data, rimg.data)

	cube = RubiksColorSolverGeneric(3)
	cube.enter_scan_data(data)
	cube.crunch_colors()
	return ''.join(cube.cube_for_kociemba_strict())

solver_strict	= CubeScan()
solver_result	= kociemba.solve( solver_strict )
print( solver_result )
