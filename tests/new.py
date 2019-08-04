#!/usr/bin/python3 

import os
import sys
import maestro
#import cv2
import time
from rubikscubetracker import RubiksImage, merge_two_dicts
from rubikscolorresolver import RubiksColorSolverGeneric
import json
import kociemba


DELAY 					= 0.1

TOP_GRIP 				= 9
BOTTOM_GRIP 			= 8
RIGHT_GRIP 				= 7
LEFT_GRIP 				= 6

TOP_ARM 				= 3
BOTTOM_ARM 				= 2
RIGHT_ARM				= 1
LEFT_ARM				= 0

TOP_FLUSH 				= 1650
BOTTOM_FLUSH 			= 1400
RIGHT_FLUSH 			= 800
LEFT_FLUSH 				= 800

TOP_FORWARD 			= 750
BOTTOM_FORWARD 			= 500
RIGHT_FORWARD 			= 1700
LEFT_FORWARD 			= 1800

TOP_NEUTRAL 			= 1870
BOTTOM_NEUTRAL 			= 1870
RIGHT_NEUTRAL 			= 1900
LEFT_NEUTRAL 			= 1870  

TOP_CLOCKWISE 			= 2500
BOTTOM_CLOCKWISE 		= 2500
RIGHT_CLOCKWISE 		= 2600
LEFT_CLOCKWISE 			= 2500

TOP_180 				= 450
BOTTOM_180 				= 500
RIGHT_180 				= 550
LEFT_180 				= 500

TOP_COUNTERCLOCKWISE 	= 1150
BOTTOM_COUNTERCLOCKWISE = 1150
RIGHT_COUNTERCLOCKWISE 	= 1175
LEFT_COUNTERCLOCKWISE 	= 1100

MAESTRO                 = maestro.Controller()

MAESTRO.set_acceleration(TOP_ARM, 200)
MAESTRO.set_acceleration(BOTTOM_ARM, 200)
MAESTRO.set_acceleration(LEFT_ARM, 200)
MAESTRO.set_acceleration(RIGHT_ARM, 200)

MAESTRO.set_acceleration(TOP_GRIP, 200)
MAESTRO.set_acceleration(BOTTOM_GRIP, 200)
MAESTRO.set_acceleration(LEFT_GRIP, 200)
MAESTRO.set_acceleration(RIGHT_GRIP, 200)

MAESTRO.set_speed(TOP_ARM, 200)
MAESTRO.set_speed(BOTTOM_ARM, 200)
MAESTRO.set_speed(LEFT_ARM, 200)
MAESTRO.set_speed(RIGHT_ARM, 200)

MAESTRO.set_speed(TOP_GRIP, 200)
MAESTRO.set_speed(BOTTOM_GRIP, 200)
MAESTRO.set_speed(LEFT_GRIP, 200)
MAESTRO.set_speed(RIGHT_GRIP, 200)



def retract_top():
    MAESTRO.set_target(TOP_ARM, TOP_FLUSH)
    time.sleep(DELAY)

def retract_bottom():
    if MAESTRO.get_position(LEFT_ARM) != LEFT_FORWARD:
        extend_left()
    if MAESTRO.get_position(RIGHT_ARM) != RIGHT_FORWARD:
        extend_right()
    MAESTRO.set_target(BOTTOM_ARM, BOTTOM_FLUSH)
    time.sleep(DELAY)    

def retract_left():
    if MAESTRO.get_position(BOTTOM_ARM) != BOTTOM_FORWARD:
        extend_bottom()
    MAESTRO.set_target(LEFT_ARM, LEFT_FLUSH)
    time.sleep(DELAY)

def retract_right():
    if MAESTRO.get_position(BOTTOM_ARM) != BOTTOM_FORWARD:
        extend_bottom()
    MAESTRO.set_target(RIGHT_ARM, RIGHT_FLUSH)
    time.sleep(DELAY)

def retract_sides():
    MAESTRO.set_target(RIGHT_ARM, RIGHT_FLUSH, False)
    MAESTRO.set_target(LEFT_ARM, LEFT_FLUSH)
    time.sleep(DELAY)

def retract_verticals():
    MAESTRO.set_target(TOP_ARM, TOP_FLUSH, False)
    MAESTRO.set_target(BOTTOM_ARM, BOTTOM_FLUSH)
    time.sleep(DELAY)

def extend_top():
    MAESTRO.set_target(TOP_ARM, TOP_FORWARD)
    time.sleep(DELAY)

def extend_bottom():
    MAESTRO.set_target(BOTTOM_ARM, BOTTOM_FORWARD)
    time.sleep(DELAY)    

def extend_left():
    MAESTRO.set_target(LEFT_ARM, LEFT_FORWARD)
    time.sleep(DELAY)

def extend_right():
    MAESTRO.set_target(RIGHT_ARM, RIGHT_FORWARD)
    time.sleep(DELAY)

def extend_sides():
    MAESTRO.set_target(LEFT_ARM, LEFT_FORWARD, False)
    MAESTRO.set_target(RIGHT_ARM, RIGHT_FORWARD)
    time.sleep(DELAY)

def extend_verticals():
    MAESTRO.set_target(TOP_ARM, TOP_FORWARD, False)
    MAESTRO.set_target(BOTTOM_ARM, BOTTOM_FORWARD)
    time.sleep(DELAY)

def turn_top_neutral():
    MAESTRO.set_target(TOP_GRIP, TOP_NEUTRAL)
    time.sleep(DELAY)

def turn_top_clockwise_90():
    if MAESTRO.get_position(TOP_GRIP) != TOP_NEUTRAL:
        if MAESTRO.get_position(TOP_ARM) == TOP_FORWARD:
            retract_top()
            turn_top_neutral()
            extend_top()
        else:
            turn_top_neutral()
    if MAESTRO.get_position(LEFT_GRIP) != LEFT_NEUTRAL:
        if MAESTRO.get_position(LEFT_ARM) == LEFT_FORWARD:
            retract_left()
            turn_left_neutral()
            extend_left()
        else:
            turn_left_neutral()
    if MAESTRO.get_position(RIGHT_GRIP) != RIGHT_NEUTRAL:
        if MAESTRO.get_position(RIGHT_ARM) == RIGHT_FORWARD:
            retract_right()
            turn_right_neutral()
            extend_right()
        else:
            turn_right_neutral()
    MAESTRO.set_target(TOP_GRIP, TOP_CLOCKWISE)
    time.sleep(DELAY)

def turn_top_180():
    if MAESTRO.get_position(TOP_GRIP) != TOP_NEUTRAL:
        if MAESTRO.get_position(TOP_ARM) == TOP_FORWARD:
            retract_top()
            turn_top_neutral()
            extend_top()
        else:
            turn_top_neutral()
    if MAESTRO.get_position(LEFT_GRIP) != LEFT_NEUTRAL:
        if MAESTRO.get_position(LEFT_ARM) == LEFT_FORWARD:
            retract_left()
            turn_left_neutral()
            extend_left()
        else:
            turn_left_neutral()
    if MAESTRO.get_position(RIGHT_GRIP) != RIGHT_NEUTRAL:
        if MAESTRO.get_position(RIGHT_ARM) == RIGHT_FORWARD:
            retract_right()
            turn_right_neutral()
            extend_right()
        else:
            turn_right_neutral()
    MAESTRO.set_target(TOP_GRIP, TOP_180)
    time.sleep(DELAY)

def turn_top_counter_clockwise_90():
    if MAESTRO.get_position(TOP_GRIP) != TOP_NEUTRAL:
        if MAESTRO.get_position(TOP_ARM) == TOP_FORWARD:
            retract_top()
            turn_top_neutral()
            extend_top()
        else:
            turn_top_neutral()
    if MAESTRO.get_position(LEFT_GRIP) != LEFT_NEUTRAL:
        if MAESTRO.get_position(LEFT_ARM) == LEFT_FORWARD:
            retract_left()
            turn_left_neutral()
            extend_left()
        else:
            turn_left_neutral()
    if MAESTRO.get_position(RIGHT_GRIP) != RIGHT_NEUTRAL:
        if MAESTRO.get_position(RIGHT_ARM) == RIGHT_FORWARD:
            retract_right()
            turn_right_neutral()
            extend_right()
        else:
            turn_right_neutral()
    MAESTRO.set_target(TOP_GRIP, TOP_COUNTERCLOCKWISE)
    time.sleep(DELAY)

def turn_bottom_neutral():
    MAESTRO.set_target(BOTTOM_GRIP, BOTTOM_NEUTRAL)
    time.sleep(DELAY)

def turn_bottom_clockwise_90():
    if MAESTRO.get_position(BOTTOM_GRIP) != BOTTOM_NEUTRAL:
        if MAESTRO.get_position(BOTTOM_ARM) == BOTTOM_FORWARD:
            retract_bottom()
            turn_bottom_neutral()
            extend_bottom()
        else:
            turn_bottom_neutral()
    if MAESTRO.get_position(LEFT_GRIP) != LEFT_NEUTRAL:
        if MAESTRO.get_position(LEFT_ARM) == LEFT_FORWARD:
            retract_left()
            turn_left_neutral()
            extend_left()
        else:
            turn_left_neutral()
    if MAESTRO.get_position(RIGHT_GRIP) != RIGHT_NEUTRAL:
        if MAESTRO.get_position(RIGHT_ARM) == RIGHT_FORWARD:
            retract_right()
            turn_right_neutral()
            extend_right()
        else:
            turn_right_neutral()
    MAESTRO.set_target(BOTTOM_GRIP, BOTTOM_CLOCKWISE)
    time.sleep(DELAY)

def turn_bottom_180():
    if MAESTRO.get_position(BOTTOM_GRIP) != BOTTOM_NEUTRAL:
        if MAESTRO.get_position(BOTTOM_ARM) == BOTTOM_FORWARD:
            retract_bottom()
            turn_bottom_neutral()
            extend_bottom()
        else:
            turn_bottom_neutral()
    if MAESTRO.get_position(LEFT_GRIP) != LEFT_NEUTRAL:
        if MAESTRO.get_position(LEFT_ARM) == LEFT_FORWARD:
            retract_left()
            turn_left_neutral()
            extend_left()
        else:
            turn_left_neutral()
    if MAESTRO.get_position(RIGHT_GRIP) != RIGHT_NEUTRAL:
        if MAESTRO.get_position(RIGHT_ARM) == RIGHT_FORWARD:
            retract_right()
            turn_right_neutral()
            extend_right()
        else:
            turn_right_neutral()
    MAESTRO.set_target(BOTTOM_GRIP, BOTTOM_180)
    time.sleep(DELAY)

def turn_bottom_counter_clockwise_90():
    if MAESTRO.get_position(BOTTOM_GRIP) != BOTTOM_NEUTRAL:
        if MAESTRO.get_position(BOTTOM_ARM) == BOTTOM_FORWARD:
            retract_bottom()
            turn_bottom_neutral()
            extend_bottom()
        else:
            turn_bottom_neutral()
    if MAESTRO.get_position(LEFT_GRIP) != LEFT_NEUTRAL:
        if MAESTRO.get_position(LEFT_ARM) == LEFT_FORWARD:
            retract_left()
            turn_left_neutral()
            extend_left()
        else:
            turn_left_neutral()
    if MAESTRO.get_position(RIGHT_GRIP) != RIGHT_NEUTRAL:
        if MAESTRO.get_position(RIGHT_ARM) == RIGHT_FORWARD:
            retract_right()
            turn_right_neutral()
            extend_right()
        else:
            turn_right_neutral()
    MAESTRO.set_target(BOTTOM_GRIP, BOTTOM_COUNTERCLOCKWISE)
    time.sleep(DELAY)

def turn_left_neutral():
    MAESTRO.set_target(LEFT_GRIP, LEFT_NEUTRAL)
    time.sleep(DELAY)

def turn_left_clockwise_90():
    if MAESTRO.get_position(LEFT_GRIP) != LEFT_NEUTRAL:
        if MAESTRO.get_position(LEFT_ARM) == LEFT_FORWARD:
            retract_left()
            turn_left_neutral()
            extend_left()
        else:
            turn_left_neutral()
    if MAESTRO.get_position(TOP_GRIP) != TOP_NEUTRAL:
        if MAESTRO.get_position(TOP_ARM) == TOP_FORWARD:
            retract_top()
            turn_top_neutral()
            extend_top()
        else:
            turn_top_neutral()
    if MAESTRO.get_position(BOTTOM_GRIP) != BOTTOM_NEUTRAL:
        if MAESTRO.get_position(BOTTOM_ARM) == BOTTOM_FORWARD:
            retract_bottom()
            turn_bottom_neutral()
            extend_bottom()
        else:
            turn_bottom_neutral()
    MAESTRO.set_target(LEFT_GRIP, LEFT_CLOCKWISE)
    time.sleep(DELAY)

def turn_left_180():
    if MAESTRO.get_position(LEFT_GRIP) != LEFT_NEUTRAL:
        if MAESTRO.get_position(LEFT_ARM) == LEFT_FORWARD:
            retract_left()
            turn_left_neutral()
            extend_left()
        else:
            turn_left_neutral()
    if MAESTRO.get_position(TOP_GRIP) != TOP_NEUTRAL:
        if MAESTRO.get_position(TOP_ARM) == TOP_FORWARD:
            retract_top()
            turn_top_neutral()
            extend_top()
        else:
            turn_top_neutral()
    if MAESTRO.get_position(BOTTOM_GRIP) != BOTTOM_NEUTRAL:
        if MAESTRO.get_position(BOTTOM_ARM) == BOTTOM_FORWARD:
            retract_bottom()
            turn_bottom_neutral()
            extend_bottom()
        else:
            turn_bottom_neutral()
    MAESTRO.set_target(LEFT_GRIP, LEFT_180)
    time.sleep(DELAY)

def turn_left_counter_clockwise_90():
    if MAESTRO.get_position(LEFT_GRIP) != LEFT_NEUTRAL:
        if MAESTRO.get_position(LEFT_ARM) == LEFT_FORWARD:
            retract_left()
            turn_left_neutral()
            extend_left()
        else:
            turn_left_neutral()
    if MAESTRO.get_position(TOP_GRIP) != TOP_NEUTRAL:
        if MAESTRO.get_position(TOP_ARM) == TOP_FORWARD:
            retract_top()
            turn_top_neutral()
            extend_top()
        else:
            turn_top_neutral()
    if MAESTRO.get_position(BOTTOM_GRIP) != BOTTOM_NEUTRAL:
        if MAESTRO.get_position(BOTTOM_ARM) == BOTTOM_FORWARD:
            retract_bottom()
            turn_bottom_neutral()
            extend_bottom()
        else:
            turn_bottom_neutral()
    MAESTRO.set_target(LEFT_GRIP, LEFT_COUNTERCLOCKWISE)
    time.sleep(DELAY)

def turn_right_neutral():
    MAESTRO.set_target(RIGHT_GRIP, RIGHT_NEUTRAL)
    time.sleep(DELAY)

def turn_right_clockwise_90():
    if MAESTRO.get_position(RIGHT_GRIP) != RIGHT_NEUTRAL:
        if MAESTRO.get_position(RIGHT_ARM) == RIGHT_FORWARD:
            retract_right()
            turn_right_neutral()
            extend_right()
        else:
            turn_right_neutral()
    if MAESTRO.get_position(TOP_GRIP) != TOP_NEUTRAL:
        if MAESTRO.get_position(TOP_ARM) == TOP_FORWARD:
            retract_top()
            turn_top_neutral()
            extend_top()
        else:
            turn_top_neutral()
    if MAESTRO.get_position(BOTTOM_GRIP) != BOTTOM_NEUTRAL:
        if MAESTRO.get_position(BOTTOM_ARM) == BOTTOM_FORWARD:
            retract_bottom()
            turn_bottom_neutral()
            extend_bottom()
        else:
            turn_bottom_neutral()
    MAESTRO.set_target(RIGHT_GRIP, RIGHT_CLOCKWISE)
    time.sleep(DELAY)

def turn_right_180():
    if MAESTRO.get_position(RIGHT_GRIP) != RIGHT_NEUTRAL:
        if MAESTRO.get_position(RIGHT_ARM) == RIGHT_FORWARD:
            retract_right()
            turn_right_neutral()
            extend_right()
        else:
            turn_right_neutral()
    if MAESTRO.get_position(TOP_GRIP) != TOP_NEUTRAL:
        if MAESTRO.get_position(TOP_ARM) == TOP_FORWARD:
            retract_top()
            turn_top_neutral()
            extend_top()
        else:
            turn_top_neutral()
    if MAESTRO.get_position(BOTTOM_GRIP) != BOTTOM_NEUTRAL:
        if MAESTRO.get_position(BOTTOM_ARM) == BOTTOM_FORWARD:
            retract_bottom()
            turn_bottom_neutral()
            extend_bottom()
        else:
            turn_bottom_neutral()
    MAESTRO.set_target(RIGHT_GRIP, RIGHT_180)
    time.sleep(DELAY)

def turn_right_counter_clockwise_90():
    if MAESTRO.get_position(RIGHT_GRIP) != RIGHT_NEUTRAL:
        if MAESTRO.get_position(RIGHT_ARM) == RIGHT_FORWARD:
            retract_right()
            turn_right_neutral()
            extend_right()
        else:
            turn_right_neutral()
    if MAESTRO.get_position(TOP_GRIP) != TOP_NEUTRAL:
        if MAESTRO.get_position(TOP_ARM) == TOP_FORWARD:
            retract_top()
            turn_top_neutral()
            extend_top()
        else:
            turn_top_neutral()
    if MAESTRO.get_position(BOTTOM_GRIP) != BOTTOM_NEUTRAL:
        if MAESTRO.get_position(BOTTOM_ARM) == BOTTOM_FORWARD:
            retract_bottom()
            turn_bottom_neutral()
            extend_bottom()
        else:
            turn_bottom_neutral()
    MAESTRO.set_target(RIGHT_GRIP, RIGHT_COUNTERCLOCKWISE)
    time.sleep(DELAY)

def open_arms():
    retract_sides()
    retract_verticals()

def turn_cube_up():
    global kociemba_map
    fn_turn_right_clockwise_90 = kociemba_map['R']
    fn_turn_right_180 = kociemba_map['R2']
    fn_turn_right_counter_clockwise_90 = kociemba_map['R\'']
    fn_turn_top_clockwise_90 = kociemba_map['U']
    fn_turn_top_180 = kociemba_map['U2']
    fn_turn_top_counter_clockwise_90 = kociemba_map['U\'']
    fn_turn_front_clockwise_90 = kociemba_map['F']
    fn_turn_front_180 = kociemba_map['F2']
    fn_turn_front_counter_clockwise_90 = kociemba_map['F\'']
    fn_turn_left_clockwise_90 = kociemba_map['L']
    fn_turn_left_180 = kociemba_map['L2']
    fn_turn_left_counter_clockwise_90 = kociemba_map['L\'']
    fn_turn_back_clockwise_90 = kociemba_map['B']
    fn_turn_back_180 = kociemba_map['B2']
    fn_turn_back_counter_clockwise_90 = kociemba_map['B\'']
    fn_turn_bottom_clockwise_90 = kociemba_map['D']
    fn_turn_bottom_180 = kociemba_map['D2']
    fn_turn_bottom_counter_clockwise_90 = kociemba_map['D\'']
    extend_verticals()
    if MAESTRO.get_position(LEFT_GRIP) != LEFT_NEUTRAL:
        retract_left()
        turn_left_neutral()
        extend_left()
    if MAESTRO.get_position(RIGHT_GRIP) != RIGHT_COUNTERCLOCKWISE:
        retract_right()
        turn_right_counter_clockwise_90()
        extend_right()
    retract_verticals()
    MAESTRO.set_target(LEFT_GRIP, LEFT_COUNTERCLOCKWISE, False)
    MAESTRO.set_target(RIGHT_GRIP, RIGHT_NEUTRAL)
    time.sleep(DELAY)
    extend_verticals()
    retract_sides()
    MAESTRO.set_target(LEFT_GRIP, LEFT_NEUTRAL, False)
    MAESTRO.set_target(RIGHT_GRIP, RIGHT_NEUTRAL)
    time.sleep(DELAY)
    extend_sides()
    kociemba_map = {
        'R': fn_turn_right_clockwise_90,
        'R2': fn_turn_right_180,
        'R\'': fn_turn_right_counter_clockwise_90,
        'U': fn_turn_back_clockwise_90,
        'U2': fn_turn_back_180,
        'U\'': fn_turn_back_counter_clockwise_90,
        'F': fn_turn_top_clockwise_90,
        'F2': fn_turn_top_180,
        'F\'': fn_turn_top_counter_clockwise_90,
        'L': fn_turn_left_clockwise_90,
        'L2': fn_turn_left_180,
        'L\'': fn_turn_left_counter_clockwise_90,
        'B': fn_turn_bottom_clockwise_90,
        'B2': fn_turn_bottom_180,
        'B\'': fn_turn_bottom_counter_clockwise_90,
        'D': fn_turn_front_clockwise_90,
        'D2': fn_turn_front_180,
        'D\'': fn_turn_front_counter_clockwise_90
    }

def turn_cube_down():
    global kociemba_map
    fn_turn_right_clockwise_90 = kociemba_map['R']
    fn_turn_right_180 = kociemba_map['R2']
    fn_turn_right_counter_clockwise_90 = kociemba_map['R\'']
    fn_turn_top_clockwise_90 = kociemba_map['U']
    fn_turn_top_180 = kociemba_map['U2']
    fn_turn_top_counter_clockwise_90 = kociemba_map['U\'']
    fn_turn_front_clockwise_90 = kociemba_map['F']
    fn_turn_front_180 = kociemba_map['F2']
    fn_turn_front_counter_clockwise_90 = kociemba_map['F\'']
    fn_turn_left_clockwise_90 = kociemba_map['L']
    fn_turn_left_180 = kociemba_map['L2']
    fn_turn_left_counter_clockwise_90 = kociemba_map['L\'']
    fn_turn_back_clockwise_90 = kociemba_map['B']
    fn_turn_back_180 = kociemba_map['B2']
    fn_turn_back_counter_clockwise_90 = kociemba_map['B\'']
    fn_turn_bottom_clockwise_90 = kociemba_map['D']
    fn_turn_bottom_180 = kociemba_map['D2']
    fn_turn_bottom_counter_clockwise_90 = kociemba_map['D\'']
    if MAESTRO.get_position(LEFT_GRIP) != LEFT_COUNTERCLOCKWISE:
        retract_left()
        turn_left_counter_clockwise_90()
        extend_left()
    if MAESTRO.get_position(RIGHT_GRIP) != RIGHT_NEUTRAL:
        retract_right()
        turn_right_neutral()
        extend_right()
    retract_verticals()
    MAESTRO.set_target(LEFT_GRIP, LEFT_NEUTRAL, False)
    MAESTRO.set_target(RIGHT_GRIP, RIGHT_COUNTERCLOCKWISE)
    time.sleep(DELAY)
    extend_verticals()
    retract_sides()
    MAESTRO.set_target(LEFT_GRIP, LEFT_NEUTRAL, False)
    MAESTRO.set_target(RIGHT_GRIP, RIGHT_NEUTRAL)
    time.sleep(DELAY)
    extend_sides()
    kociemba_map.update({
        'R': fn_turn_right_clockwise_90,
        'R2': fn_turn_right_180,
        'R\'': fn_turn_right_counter_clockwise_90,
        'U': fn_turn_front_clockwise_90,
        'U2': fn_turn_front_180,
        'U\'': fn_turn_front_counter_clockwise_90,
        'F': fn_turn_bottom_clockwise_90,
        'F2': fn_turn_bottom_180,
        'F\'': fn_turn_bottom_counter_clockwise_90,
        'L': fn_turn_left_clockwise_90,
        'L2': fn_turn_left_180,
        'L\'': fn_turn_left_counter_clockwise_90,
        'B': fn_turn_top_clockwise_90,
        'B2': fn_turn_top_180,
        'B\'': fn_turn_top_counter_clockwise_90,
        'D': fn_turn_back_clockwise_90,
        'D2': fn_turn_back_180,
        'D\'': fn_turn_bottom_counter_clockwise_90
    })

def turn_cube_left():
    global kociemba_map
    fn_turn_right_clockwise_90 = kociemba_map['R']
    fn_turn_right_180 = kociemba_map['R2']
    fn_turn_right_counter_clockwise_90 = kociemba_map['R\'']
    fn_turn_top_clockwise_90 = kociemba_map['U']
    fn_turn_top_180 = kociemba_map['U2']
    fn_turn_top_counter_clockwise_90 = kociemba_map['U\'']
    fn_turn_front_clockwise_90 = kociemba_map['F']
    fn_turn_front_180 = kociemba_map['F2']
    fn_turn_front_counter_clockwise_90 = kociemba_map['F\'']
    fn_turn_left_clockwise_90 = kociemba_map['L']
    fn_turn_left_180 = kociemba_map['L2']
    fn_turn_left_counter_clockwise_90 = kociemba_map['L\'']
    fn_turn_back_clockwise_90 = kociemba_map['B']
    fn_turn_back_180 = kociemba_map['B2']
    fn_turn_back_counter_clockwise_90 = kociemba_map['B\'']
    fn_turn_bottom_clockwise_90 = kociemba_map['D']
    fn_turn_bottom_180 = kociemba_map['D2']
    fn_turn_bottom_counter_clockwise_90 = kociemba_map['D\'']
    extend_sides()
    if MAESTRO.get_position(TOP_GRIP) != TOP_NEUTRAL:
        retract_top()
        turn_top_neutral()
        extend_top()
    if MAESTRO.get_position(BOTTOM_GRIP) != BOTTOM_COUNTERCLOCKWISE:
        retract_bottom()
        turn_bottom_clockwise_90()
        extend_bottom()
    retract_sides()
    MAESTRO.set_target(TOP_GRIP, TOP_CLOCKWISE, False)
    MAESTRO.set_target(BOTTOM_GRIP, BOTTOM_NEUTRAL)
    time.sleep(DELAY)
    extend_sides()
    retract_verticals()
    MAESTRO.set_target(TOP_GRIP, TOP_NEUTRAL, False)
    MAESTRO.set_target(BOTTOM_GRIP, BOTTOM_NEUTRAL)
    time.sleep(DELAY)
    extend_verticals()
    kociemba_map.update({
        'R': fn_turn_front_clockwise_90,
        'R2': fn_turn_front_180,
        'R\'': fn_turn_front_counter_clockwise_90,
        'U': fn_turn_top_clockwise_90,
        'U2': fn_turn_top_180,
        'U\'': fn_turn_top_counter_clockwise_90,
        'F': fn_turn_left_clockwise_90,
        'F2': fn_turn_left_180,
        'F\'': fn_turn_left_counter_clockwise_90,
        'L': fn_turn_back_clockwise_90,
        'L2': fn_turn_back_180,
        'L\'': fn_turn_back_counter_clockwise_90,
        'B': fn_turn_right_clockwise_90,
        'B2': fn_turn_right_180,
        'B\'': fn_turn_right_counter_clockwise_90,
        'D': fn_turn_bottom_clockwise_90,
        'D2': fn_turn_bottom_180,
        'D\'': fn_turn_bottom_counter_clockwise_90
    })

def turn_cube_right():
    global kociemba_map
    fn_turn_right_clockwise_90 = kociemba_map['R']
    fn_turn_right_180 = kociemba_map['R2']
    fn_turn_right_counter_clockwise_90 = kociemba_map['R\'']
    fn_turn_top_clockwise_90 = kociemba_map['U']
    fn_turn_top_180 = kociemba_map['U2']
    fn_turn_top_counter_clockwise_90 = kociemba_map['U\'']
    fn_turn_front_clockwise_90 = kociemba_map['F']
    fn_turn_front_180 = kociemba_map['F2']
    fn_turn_front_counter_clockwise_90 = kociemba_map['F\'']
    fn_turn_left_clockwise_90 = kociemba_map['L']
    fn_turn_left_180 = kociemba_map['L2']
    fn_turn_left_counter_clockwise_90 = kociemba_map['L\'']
    fn_turn_back_clockwise_90 = kociemba_map['B']
    fn_turn_back_180 = kociemba_map['B2']
    fn_turn_back_counter_clockwise_90 = kociemba_map['B\'']
    fn_turn_bottom_clockwise_90 = kociemba_map['D']
    fn_turn_bottom_180 = kociemba_map['D2']
    fn_turn_bottom_counter_clockwise_90 = kociemba_map['D\'']
    extend_sides()
    if MAESTRO.get_position(TOP_GRIP) != TOP_CLOCKWISE:
        retract_top()
        turn_top_clockwise_90()
        extend_top()
    if MAESTRO.get_position(BOTTOM_GRIP) != BOTTOM_NEUTRAL:
        retract_bottom()
        turn_bottom_neutral()
        extend_bottom()
    retract_sides()
    MAESTRO.set_target(TOP_GRIP, TOP_NEUTRAL, False)
    MAESTRO.set_target(BOTTOM_GRIP, BOTTOM_CLOCKWISE)
    time.sleep(DELAY)
    extend_sides()
    retract_verticals()
    MAESTRO.set_target(TOP_GRIP, TOP_NEUTRAL, False)
    MAESTRO.set_target(BOTTOM_GRIP, BOTTOM_NEUTRAL)
    time.sleep(DELAY)
    extend_verticals()
    kociemba_map.update({
        'R': fn_turn_back_clockwise_90,
        'R2': fn_turn_back_180,
        'R\'': fn_turn_back_counter_clockwise_90,
        'U': fn_turn_top_clockwise_90,
        'U2': fn_turn_top_180,
        'U\'': fn_turn_top_counter_clockwise_90,
        'F': fn_turn_right_clockwise_90,
        'F2': fn_turn_right_180,
        'F\'': fn_turn_right_counter_clockwise_90,
        'L': fn_turn_front_clockwise_90,
        'L2': fn_turn_front_180,
        'L\'': fn_turn_front_counter_clockwise_90,
        'B': fn_turn_left_clockwise_90,
        'B2': fn_turn_left_180,
        'B\'': fn_turn_left_counter_clockwise_90,
        'D': fn_turn_bottom_clockwise_90,
        'D2': fn_turn_bottom_180,
        'D\'': fn_turn_bottom_counter_clockwise_90
    })


def turn_front_clockwise_90():
    turn_cube_right()
    turn_right_clockwise_90()

def turn_front_180():
    turn_cube_right()
    turn_right_180()

def turn_front_counter_clockwise_90():
    turn_cube_right()
    turn_right_counter_clockwise_90()

def turn_back_clockwise_90():
    turn_cube_right()
    turn_left_clockwise_90()

def turn_back_180():
    turn_cube_right()
    turn_left_180()

def turn_back_counter_clockwise_90():
    turn_cube_right()
    turn_left_counter_clockwise_90()



kociemba_map = {
'R': turn_right_clockwise_90,
'R2': turn_right_180,
'R\'': turn_right_counter_clockwise_90,
'U': turn_top_clockwise_90,
'U2': turn_top_180,
'U\'': turn_top_counter_clockwise_90,
'F': turn_front_clockwise_90,
'F2': turn_front_180,
'F\'': turn_front_counter_clockwise_90,
'L': turn_left_clockwise_90,
'L2': turn_left_180,
'L\'': turn_left_counter_clockwise_90,
'B': turn_back_clockwise_90,
'B2': turn_back_180,
'B\'': turn_back_counter_clockwise_90,
'D': turn_bottom_clockwise_90,
'D2': turn_bottom_180,
'D\'': turn_bottom_counter_clockwise_90
}

def take_picture(filename):
    camera = cv2.VideoCapture(0)
    camera.set(cv2.cv.CV_CAP_PROP_BRIGHTNESS, 0.5)
    camera.set(cv2.cv.CV_CAP_PROP_SATURATION, 0.35)
    camera.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, 480)
    for i in range(30):
        ret, image = camera.read()
    ret, image = camera.read()
    cv2.imwrite(filename, image)
    camera.release()

def get_cube_state():
    data = {}
    if not os.path.exists(os.path.join(os.getcwd(), "CUBE_STATE")):
         os.mkdir(os.path.join(os.getcwd(), "CUBE_STATE"))
    extend_sides()
    retract_verticals()
    MAESTRO.set_target(TOP_GRIP, TOP_COUNTERCLOCKWISE, False)
    MAESTRO.set_target(BOTTOM_GRIP, BOTTOM_COUNTERCLOCKWISE)
    time.sleep(DELAY)    
    extend_verticals()
    retract_sides()
    take_picture(os.path.join(os.getcwd(), "CUBE_STATE", "rubiks-side-F.png"))
    MAESTRO.set_target(TOP_GRIP, TOP_180, False)
    MAESTRO.set_target(BOTTOM_GRIP, BOTTOM_NEUTRAL,)
    time.sleep(DELAY)
    extend_sides()
    retract_verticals()
    MAESTRO.set_target(TOP_GRIP, TOP_COUNTERCLOCKWISE, False)
    MAESTRO.set_target(BOTTOM_GRIP, BOTTOM_COUNTERCLOCKWISE)
    time.sleep(DELAY)  
    extend_verticals()
    retract_sides()
    take_picture(os.path.join(os.getcwd(), "CUBE_STATE", "rubiks-side-L.png"))
    MAESTRO.set_target(TOP_GRIP, TOP_180, False)
    MAESTRO.set_target(BOTTOM_GRIP, BOTTOM_NEUTRAL)
    time.sleep(DELAY)
    extend_sides()
    retract_verticals()
    MAESTRO.set_target(TOP_GRIP, TOP_COUNTERCLOCKWISE, False)
    MAESTRO.set_target(BOTTOM_GRIP, BOTTOM_COUNTERCLOCKWISE,)
    time.sleep(DELAY)  
    extend_verticals()
    retract_sides()
    take_picture(os.path.join(os.getcwd(), "CUBE_STATE", "rubiks-side-B.png"))
    MAESTRO.set_target(TOP_GRIP, TOP_180, False)
    MAESTRO.set_target(BOTTOM_GRIP, BOTTOM_NEUTRAL)
    time.sleep(DELAY)
    extend_sides()
    retract_verticals()
    MAESTRO.set_target(TOP_GRIP, TOP_COUNTERCLOCKWISE, False)
    MAESTRO.set_target(BOTTOM_GRIP, BOTTOM_COUNTERCLOCKWISE)
    time.sleep(DELAY)  
    extend_verticals()
    retract_sides()
    take_picture(os.path.join(os.getcwd(), "CUBE_STATE", "rubiks-side-R.png"))
    MAESTRO.set_target(TOP_GRIP, TOP_180, False)
    MAESTRO.set_target(BOTTOM_GRIP, BOTTOM_NEUTRAL)
    time.sleep(DELAY)
    extend_sides()
    retract_verticals()
    MAESTRO.set_target(TOP_GRIP, TOP_NEUTRAL, False)
    MAESTRO.set_target(BOTTOM_GRIP, BOTTOM_NEUTRAL)
    time.sleep(DELAY)
    MAESTRO.set_target(LEFT_GRIP, LEFT_COUNTERCLOCKWISE, False)
    MAESTRO.set_target(RIGHT_GRIP, RIGHT_CLOCKWISE)
    time.sleep(DELAY)
    take_picture(os.path.join(os.getcwd(), "CUBE_STATE", "rubiks-side-D.png"))
    MAESTRO.set_target(LEFT_GRIP, LEFT_CLOCKWISE, False)
    MAESTRO.set_target(RIGHT_GRIP, RIGHT_COUNTERCLOCKWISE)  
    take_picture(os.path.join(os.getcwd(), "CUBE_STATE", "rubiks-side-U.png"))
    MAESTRO.set_target(LEFT_GRIP, LEFT_NEUTRAL, False)
    MAESTRO.set_target(RIGHT_GRIP, RIGHT_NEUTRAL)
    extend_verticals()

    for (side_index, side_name) in enumerate(('U', 'L', 'F', 'R', 'B', 'D')):
        filename = os.path.join(os.getcwd(), "CUBE_STATE", "rubiks-side-%s.png" % side_name)
        rimg = RubiksImage(side_index, side_name)
        rimg.analyze_file(filename)
        data = merge_two_dicts(data, rimg.data)
    cube = RubiksColorSolverGeneric(3)
    cube.enter_scan_data(data)
    cube.crunch_colors()
    return ''.join(cube.cube_for_kociemba_strict())
    


def get_solution(state):
     return kociemba.solve(state)
    

def solve(solution):
    for move in solution.split(" "):
        move_function = kociemba_map[move]
        move_function()

def main():
    extend_verticals()
    extend_sides()
    state = get_cube_state()
    solution = get_solution(state)
    solve(solution)
    open_arms()

def click(event, x, y, flags, param): 
    global SOLVED
    if x > 450 or x < 0:
        sys.exit(0)
    if event == cv2.EVENT_LBUTTONUP and not SOLVED:
        main()
        SOLVED = True
    elif event == cv2.EVENT_LBUTTONUP and SOLVED:
        open_arms()
        turn_top_neutral()
        turn_left_neutral()
        turn_bottom_neutral()
        turn_right_neutral()
        SOLVED = False

SOLVED = False

"""
if __name__  == '__main__':
    while True:
	    fortegobot = cv2.imread('fortegobot.jpg')
            cv2.namedWindow('Go bot go!', cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty('Go bot go!', cv2.WND_PROP_FULLSCREEN, 1)
	    cv2.imshow('Go bot go!', fortegobot)
            cv2.setMouseCallback('Go bot go!', click)
	    open_arms()
	    turn_top_neutral()
	    turn_left_neutral()
	    turn_bottom_neutral()
	    turn_right_neutral()
            cv2.waitKey(0)
"""
