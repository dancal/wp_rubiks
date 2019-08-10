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

	#return 'DRLUUBFBRBLURRLRUBLRDDFDLFUFUFFDBRDUBRUFLLFDDBFLUBLRBD'
	#return 'UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB'
	#return 'UUUUUUUUULLLLLLLLLFFFFFFFFFRRRRRRRRRBBBBBBBBBDDDDDDDDD'

	#data = json.loads(str)
	data = {}
	# F,R,B,L,U,D
	#  (letters stand for Up, Left, Front, Right, Back, and Down)
	#for (side_index, side_name) in enumerate(('U', 'R', 'F', 'D', 'L', 'B')):
	for (side_index, side_name) in enumerate(('U', 'R', 'F', 'D', 'L', 'B')):
		index = 0
		if side_name == 'U':
			index = 4
		elif side_name == 'L':
			index = 1
		elif side_name == 'F':
			index = 0
		elif side_name == 'R':
			index = 2
		elif side_name == 'B':
			index = 3
		elif side_name == 'D':
			index = 5

		filename = os.path.join(os.getcwd(), "images", "%s.png" % index)
		print('file = ', filename)
		rimg = RubiksImage(index, side_name)
		rimg.analyze_file(filename)
		data = merge_two_dicts(data, rimg.data)

	cube = RubiksColorSolverGeneric(3)
	cube.enter_scan_data(data)
	cube.crunch_colors()
	return ''.join(cube.cube_for_kociemba_strict())

solver_strict	= CubeScan()
solver_result	= kociemba.solve( solver_strict )
print( solver_result )
