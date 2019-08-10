#!/usr/bin/python
#################################################################################
# 2019.07.25. created by dancal
#################################################################################

import sys
import time 
import json
import threading
import maestro

def load_config_file( file ):
    with open(file, 'r') as f:
        config = json.load(f)
    return config

def get_config_value( CONFIG, servo_name, key ):
	return CONFIG['servos'][servo_name][key]

DELAY                   = 1 
SERVO_ACCEL				= 200

SYSTEM_CONFIG_FILE		= 'config.json'
SYSTEM_CONFIG			= load_config_file( SYSTEM_CONFIG_FILE );

ARM_RIGHT_NAME			= 'a1'
ARM_TOP_NAME			= 'a2'
ARM_LEFT_NAME			= 'a3'
ARM_BOTTOM_NAME			= 'a4'

GRIP_RIGHT_NAME			= 'g1'
GRIP_TOP_NAME			= 'g2'
GRIP_LEFT_NAME			= 'g3'
GRIP_BOTTOM_NAME		= 'g4'

#################################################################################
#
#################################################################################
ARM_RIGHT               = get_config_value( SYSTEM_CONFIG, ARM_RIGHT_NAME, 's' )
ARM_TOP                 = get_config_value( SYSTEM_CONFIG, ARM_TOP_NAME, 's' )
ARM_LEFT                = get_config_value( SYSTEM_CONFIG, ARM_LEFT_NAME, 's' )
ARM_BOTTOM              = get_config_value( SYSTEM_CONFIG, ARM_BOTTOM_NAME, 's' )

ARM_NEAR_RIGHT			= get_config_value( SYSTEM_CONFIG, ARM_RIGHT_NAME, 'low' )
ARM_NEAR_TOP			= get_config_value( SYSTEM_CONFIG, ARM_TOP_NAME, 'low' )
ARM_NEAR_LEFT			= get_config_value( SYSTEM_CONFIG, ARM_LEFT_NAME, 'low' )
ARM_NEAR_BOTTOM			= get_config_value( SYSTEM_CONFIG, ARM_BOTTOM_NAME, 'low' )

ARM_FAR_RIGHT			= get_config_value( SYSTEM_CONFIG, ARM_RIGHT_NAME, 'high' )
ARM_FAR_TOP				= get_config_value( SYSTEM_CONFIG, ARM_TOP_NAME, 'high' )
ARM_FAR_LEFT			= get_config_value( SYSTEM_CONFIG, ARM_LEFT_NAME, 'high' )
ARM_FAR_BOTTOM			= get_config_value( SYSTEM_CONFIG, ARM_BOTTOM_NAME, 'high' )

#################################################################################
#
#################################################################################
GRIP_RIGHT              = get_config_value( SYSTEM_CONFIG, GRIP_RIGHT_NAME, 's' )
GRIP_TOP                = get_config_value( SYSTEM_CONFIG, GRIP_TOP_NAME, 's' )
GRIP_LEFT               = get_config_value( SYSTEM_CONFIG, GRIP_LEFT_NAME, 's' )
GRIP_BOTTOM             = get_config_value( SYSTEM_CONFIG, GRIP_BOTTOM_NAME, 's' )

GRIP_NEAR_RIGHT			= get_config_value( SYSTEM_CONFIG, GRIP_RIGHT_NAME, 'low' )
GRIP_NEAR_TOP			= get_config_value( SYSTEM_CONFIG, GRIP_TOP_NAME, 'low' )
GRIP_NEAR_LEFT			= get_config_value( SYSTEM_CONFIG, GRIP_LEFT_NAME, 'low' )
GRIP_NEAR_BOTTOM		= get_config_value( SYSTEM_CONFIG, GRIP_BOTTOM_NAME, 'low' )

GRIP_FAR_RIGHT			= get_config_value( SYSTEM_CONFIG, GRIP_RIGHT_NAME, 'high' )
GRIP_FAR_TOP			= get_config_value( SYSTEM_CONFIG, GRIP_TOP_NAME, 'high' )
GRIP_FAR_LEFT			= get_config_value( SYSTEM_CONFIG, GRIP_LEFT_NAME, 'high' )
GRIP_FAR_BOTTOM			= get_config_value( SYSTEM_CONFIG, GRIP_BOTTOM_NAME, 'high' )

GRIP_FAR_RIGHT			= get_config_value( SYSTEM_CONFIG, GRIP_RIGHT_NAME, 'high' )
GRIP_FAR_TOP			= get_config_value( SYSTEM_CONFIG, GRIP_TOP_NAME, 'high' )
GRIP_FAR_LEFT			= get_config_value( SYSTEM_CONFIG, GRIP_LEFT_NAME, 'high' )
GRIP_FAR_BOTTOM			= get_config_value( SYSTEM_CONFIG, GRIP_BOTTOM_NAME, 'high' )

MAESTRO					= maestro.Controller()

MAESTRO.set_acceleration(ARM_RIGHT, SERVO_ACCEL)
MAESTRO.set_acceleration(ARM_TOP, SERVO_ACCEL)
MAESTRO.set_acceleration(ARM_LEFT, SERVO_ACCEL)
MAESTRO.set_acceleration(ARM_BOTTOM, SERVO_ACCEL)

MAESTRO.set_acceleration(GRIP_RIGHT, SERVO_ACCEL)
MAESTRO.set_acceleration(GRIP_TOP, SERVO_ACCEL)
MAESTRO.set_acceleration(GRIP_LEFT, SERVO_ACCEL)
MAESTRO.set_acceleration(GRIP_BOTTOM, SERVO_ACCEL)

MAESTRO.set_speed(ARM_RIGHT, SERVO_ACCEL)
MAESTRO.set_speed(ARM_TOP, SERVO_ACCEL)
MAESTRO.set_speed(ARM_LEFT, SERVO_ACCEL)
MAESTRO.set_speed(ARM_BOTTOM, SERVO_ACCEL)

MAESTRO.set_speed(GRIP_RIGHT, SERVO_ACCEL)
MAESTRO.set_speed(GRIP_TOP, SERVO_ACCEL)
MAESTRO.set_speed(GRIP_LEFT, SERVO_ACCEL)
MAESTRO.set_speed(GRIP_BOTTOM, SERVO_ACCEL)

def MoveServoNear( servo ):
	global MAESTRO

	useSleep	= True
	postion	= ARM_NEAR_TOP
	if servo == ARM_RIGHT:
		postion	= ARM_NEAR_RIGHT
		if MAESTRO.get_position(ARM_RIGHT) == ARM_NEAR_RIGHT:
			useSleep	= False
	elif servo == ARM_TOP:
		postion	= ARM_NEAR_TOP
		if MAESTRO.get_position(ARM_TOP) == ARM_NEAR_TOP:
			useSleep	= False
	elif servo == ARM_LEFT:
		postion	= ARM_NEAR_LEFT
		if MAESTRO.get_position(ARM_LEFT) == ARM_NEAR_LEFT:
			useSleep	= False
	elif servo == ARM_BOTTOM:
		postion	= ARM_NEAR_BOTTOM
		if MAESTRO.get_position(ARM_BOTTOM) == ARM_NEAR_BOTTOM:
			useSleep	= False
	elif servo == GRIP_RIGHT:
		postion	= GRIP_NEAR_RIGHT
		if MAESTRO.get_position(GRIP_RIGHT) == GRIP_NEAR_RIGHT:
			useSleep	= False
	elif servo == GRIP_TOP:
		postion	= GRIP_NEAR_TOP
		if MAESTRO.get_position(GRIP_TOP) == GRIP_NEAR_TOP:
			useSleep	= False
	elif servo == GRIP_LEFT:
		postion	= GRIP_NEAR_LEFT
		if MAESTRO.get_position(GRIP_LEFT) == GRIP_NEAR_LEFT:
			useSleep	= False
	elif servo == GRIP_BOTTOM:
		postion	= GRIP_NEAR_BOTTOM
		if MAESTRO.get_position(GRIP_BOTTOM) == GRIP_NEAR_BOTTOM:
			useSleep	= False
		
	MAESTRO.set_target(servo, postion)
	if useSleep:
		time.sleep(DELAY)

def MoveServoFar( servo ):
	global MAESTRO

	useSleep	= True
	postion	= ARM_FAR_TOP
	if servo == ARM_RIGHT:
		postion	= ARM_FAR_RIGHT
		if MAESTRO.get_position(ARM_RIGHT) == ARM_FAR_RIGHT:
			useSleep	= False
	elif servo == ARM_TOP:
		postion	= ARM_FAR_TOP
		if MAESTRO.get_position(ARM_TOP) == ARM_FAR_TOP:
			useSleep	= False
	elif servo == ARM_LEFT:
		postion	= ARM_FAR_LEFT
		if MAESTRO.get_position(ARM_LEFT) == ARM_FAR_LEFT:
			useSleep	= False
	elif servo == ARM_BOTTOM:
		postion	= ARM_FAR_BOTTOM
		if MAESTRO.get_position(ARM_BOTTOM) == ARM_FAR_BOTTOM:
			useSleep	= False
	elif servo == GRIP_RIGHT:
		postion	= GRIP_FAR_RIGHT
		if MAESTRO.get_position(GRIP_RIGHT) == GRIP_FAR_RIGHT:
			useSleep	= False
	elif servo == GRIP_TOP:
		postion	= GRIP_FAR_TOP
		if MAESTRO.get_position(GRIP_TOP) == GRIP_FAR_TOP:
			useSleep	= False
	elif servo == GRIP_LEFT:
		postion	= GRIP_FAR_LEFT
		if MAESTRO.get_position(GRIP_LEFT) == GRIP_FAR_LEFT:
			useSleep	= False
	elif servo == GRIP_BOTTOM:
		postion	= GRIP_FAR_BOTTOM
		if MAESTRO.get_position(GRIP_BOTTOM) == GRIP_FAR_BOTTOM:
			useSleep	= False
		
	MAESTRO.set_target(servo, postion)
	if useSleep:
		time.sleep(DELAY)

def MoveServoThread( SERVO_LIST, mode ):
	servo_list	= []
	for servo in SERVO_LIST: 	
		if mode == 'Far':
			t	= threading.Thread(target=MoveServoFar, args=(servo,))
		else:
			t	= threading.Thread(target=MoveServoNear, args=(servo,))

		servo_list.append( t )
		t.start();

	for t in servo_list:
		t.join();

def MoveServoThreadCmd( SERVO_LIST, mode ):
	servo_list	= []
	for servo in SERVO_LIST: 	
		if mode == 'Far':
			t	= threading.Thread(target=MoveServoFar, args=(servo,))
		else:
			t	= threading.Thread(target=MoveServoNear, args=(servo,))

		servo_list.append( t )
		t.start();

	for t in servo_list:
		t.join();

def TurnGrip( position_str ):

	servo_arm		= eval('ARM_' + position_str)
	servo_grip		= eval('GRIP_' + position_str)
	servo_grip_far	= eval('GRIP_FAR_' + position_str );
	servo_position	= MAESTRO.get_position(servo_grip)

	if servo_position != servo_grip_far:
		MoveServoFar(servo_arm)
		MoveServoFar(servo_grip)
		MoveServoNear(servo_arm)

def MoveLeftCube( position ):
	ReadyArms()

	TurnGrip('TOP')

	# in
	#SERVO_LIST	= [ARM_TOP, ARM_BOTTOM]
	#MoveServoThread( SERVO_LIST, 'Near' )

	# out
	SERVO_LIST	= [ARM_LEFT, ARM_RIGHT]
	MoveServoThread( SERVO_LIST, 'Far' )

def InitArms():
	SERVO_LIST	= [ARM_TOP, ARM_RIGHT, ARM_LEFT, ARM_BOTTOM]
	MoveServoThread( SERVO_LIST, 'Far' )

def InitGrip():
	SERVO_LIST	= [GRIP_TOP, GRIP_RIGHT, GRIP_LEFT, GRIP_BOTTOM]
	MoveServoThread( SERVO_LIST, 'Near' )
 
def ReadyArms():
	SERVO_LIST	= [ARM_TOP, ARM_RIGHT, ARM_LEFT, ARM_BOTTOM]
	MoveServoThread( SERVO_LIST, 'Near' )

	
	

InitArms()
InitGrip()

ReadyArms()

InitArms()
#MoveLeftCube(1)

#TurnGrip('BOTTOM')
# TurnGrip('TOP')
# IintGrip('TOP')
# IintGrip('LEFT')
# IintGrip('BOTTOM')

MAESTRO.close()

"""
def servo_sleep():
    time.sleep(DELAY)

def get_servo_max_pos( servo_name ):
    global config
    servos  = config['servos']
    pos     = servos[servo_name]['high']
    return pos

def get_servo_min_pos( servo_name ):
    global config
    servos  = config['servos']
    pos     = servos[servo_name]['low']
    return pos

def get_servo_list():
    global config

    servos  = config['servos']
    keys    = list(servos.keys());
    keys.sort()
    return keys

def servo_get_arm_num( position ):
    num = 1
    if position == 'RIGHT':
        num             = 1
    elif position == 'TOP':
        num             = 3
    elif position == 'LEFT':
        num             = 5
    else:
        num             = 7

    return num

def servo_fast_move( servo, move_val ):

    num = 0
    if servo == 's1':
        num = 0
    elif servo == 's2':
        num = 1
    elif servo == 's3':
        num = 2
    elif servo == 's4':
        num = 3
    elif servo == 's5':
        num = 4
    elif servo == 's6':
        num = 5
    elif servo == 's7':
        num = 6
    elif servo == 's8':
        num = 7

    global maestro
    servo_speed = 50
    maestro.setAccel(num,servo_speed)
    maestro.setSpeed(num,servo_speed)
    maestro.setTarget(num, move_val )

def servo_slow_move( servo, move_val ):

    num = 0
    if servo == 's1':
        num = 0
    elif servo == 's2':
        num = 1
    elif servo == 's3':
        num = 2
    elif servo == 's4':
        num = 3
    elif servo == 's5':
        num = 4
    elif servo == 's6':
        num = 5
    elif servo == 's7':
        num = 6
    elif servo == 's8':
        num = 7

    global maestro
    servo_speed = 50
    maestro.setAccel(num,servo_speed)
    maestro.setSpeed(num,servo_speed)
    maestro.setTarget(num, move_val )
    servo_sleep()

def servo_unlock( position ):
    num                 = servo_get_arm_num( position )
    arm_servo_name      = 's' + str(num)
    rail_servo_name     = 's' + str(num + 1)
    arm_high_pos        = get_servo_max_pos( arm_servo_name )
    arm_low_pos         = get_servo_min_pos( arm_servo_name )
    rail_high_pos       = get_servo_max_pos( rail_servo_name )
    rail_low_pos        = get_servo_min_pos( rail_servo_name )
    servo_slow_move( rail_servo_name, rail_high_pos );        
    servo_slow_move( arm_servo_name, arm_low_pos );        

def servo_lock( position ):
    num                 = servo_get_arm_num( position )
    arm_servo_name      = 's' + str(num)
    rail_servo_name     = 's' + str(num + 1)
    arm_high_pos        = get_servo_max_pos( arm_servo_name )
    arm_low_pos         = get_servo_min_pos( arm_servo_name )
    rail_high_pos       = get_servo_max_pos( rail_servo_name )
    rail_low_pos        = get_servo_min_pos( rail_servo_name )

    servo_slow_move( arm_servo_name, arm_low_pos );        
    servo_slow_move( rail_servo_name, rail_low_pos );        

def servo_init():

    t1 = threading.Thread(target=servo_unlock, args=("TOP",))
    t2 = threading.Thread(target=servo_unlock, args=("BOTTOM",))
    t3 = threading.Thread(target=servo_unlock, args=("LEFT",))
    t4 = threading.Thread(target=servo_unlock, args=("RIGHT",))

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    t3.start()
    t4.start()
    t3.join()
    t4.join()

    servo_sleep()

def servo_ready():

    t1 = threading.Thread(target=servo_lock, args=("TOP",))
    t2 = threading.Thread(target=servo_lock, args=("BOTTOM",))
    t3 = threading.Thread(target=servo_lock, args=("LEFT",))
    t4 = threading.Thread(target=servo_lock, args=("RIGHT",))

    t1.start()
    t2.start()
    t3.start()
    t4.start()

    t1.join()
    t2.join()
    t3.join()
    t4.join()

    servo_sleep()

def servo_rail_move( position, status ):

    num                 = servo_get_arm_num( position )
    rail_servo_name     = 's' + str(num + 1)
    rail_high_pos   = get_servo_max_pos( rail_servo_name )
    rail_low_pos    = get_servo_min_pos( rail_servo_name )
    if status == 'lock':
        servo_slow_move( rail_servo_name, rail_low_pos )
    else:
        servo_slow_move( rail_servo_name, rail_high_pos )

def servo_arm_move( position, status ):

    num                 = servo_get_arm_num( position )
    arm_servo_name      = 's' + str(num)
    arm_high_pos    = get_servo_max_pos( arm_servo_name )
    arm_low_pos     = get_servo_min_pos( arm_servo_name )
    if status == 'lock':
        servo_slow_move( arm_servo_name, arm_high_pos )
    else:
        servo_slow_move( arm_servo_name, arm_low_pos )

def servo_arm_left( position ):

    num                 = servo_get_arm_num( position )
    arm_servo_name      = 's' + str(num)
    rail_servo_name     = 's' + str(num + 1)

    arm_high_pos    = get_servo_max_pos( arm_servo_name )
    arm_low_pos     = get_servo_min_pos( arm_servo_name )
    rail_high_pos   = get_servo_max_pos( rail_servo_name )
    rail_low_pos    = get_servo_min_pos( rail_servo_name )

    servo_slow_move( rail_servo_name, rail_low_pos );        
    servo_slow_move( arm_servo_name, arm_high_pos );        
    servo_slow_move( rail_servo_name, rail_high_pos );        
    servo_slow_move( arm_servo_name, arm_low_pos );        

def servo_arm_right( position ):

    num                 = servo_get_arm_num( position )
    arm_servo_name      = 's' + str(num)
    rail_servo_name     = 's' + str(num + 1)

    arm_high_pos    = get_servo_max_pos( arm_servo_name )
    arm_low_pos     = get_servo_min_pos( arm_servo_name )
    rail_high_pos   = get_servo_max_pos( rail_servo_name )
    rail_low_pos    = get_servo_min_pos( rail_servo_name )

    servo_slow_move( arm_servo_name, arm_low_pos );        
    servo_slow_move( rail_servo_name, rail_high_pos );        
    servo_slow_move( arm_servo_name, arm_high_pos );        
    servo_slow_move( rail_servo_name, rail_low_pos );        
    servo_slow_move( arm_servo_name, arm_low_pos );        

#
def servo_turn_x():

    t1 = threading.Thread(target=servo_rail_move, args=("LEFT","lock",))
    t2 = threading.Thread(target=servo_rail_move, args=("RIGHT","lock",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    t1 = threading.Thread(target=servo_rail_move, args=("TOP","unlock",))
    t2 = threading.Thread(target=servo_rail_move, args=("BOTTOM","unlock",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    t1 = threading.Thread(target=servo_arm_move, args=("TOP","lock",))
    t2 = threading.Thread(target=servo_arm_move, args=("BOTTOM","unlock",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    t1 = threading.Thread(target=servo_rail_move, args=("TOP","lock",))
    t2 = threading.Thread(target=servo_rail_move, args=("BOTTOM","lock",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    t1 = threading.Thread(target=servo_rail_move, args=("LEFT","unlock",))
    t2 = threading.Thread(target=servo_rail_move, args=("RIGHT","unlock",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    t1 = threading.Thread(target=servo_arm_move, args=("TOP","unlock",))
    t2 = threading.Thread(target=servo_arm_move, args=("BOTTOM","lock",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    t1 = threading.Thread(target=servo_rail_move, args=("LEFT","lock",))
    t2 = threading.Thread(target=servo_rail_move, args=("RIGHT","lock",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    t1 = threading.Thread(target=servo_rail_move, args=("TOP","unlock",))
    t2 = threading.Thread(target=servo_rail_move, args=("BOTTOM","unlock",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    t1 = threading.Thread(target=servo_arm_move, args=("TOP","lock",))
    t2 = threading.Thread(target=servo_arm_move, args=("BOTTOM","lock",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    t1 = threading.Thread(target=servo_rail_move, args=("TOP","lock",))
    t2 = threading.Thread(target=servo_rail_move, args=("BOTTOM","lock",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    t1 = threading.Thread(target=servo_unlock, args=("LEFT",))
    t2 = threading.Thread(target=servo_unlock, args=("RIGHT",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    t1 = threading.Thread(target=servo_rail_move, args=("LEFT","lock",))
    t2 = threading.Thread(target=servo_rail_move, args=("RIGHT","lock",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    t1 = threading.Thread(target=servo_unlock, args=("TOP",))
    t2 = threading.Thread(target=servo_unlock, args=("BOTTOM",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

################################################################
#
################################################################
config_file = 'config.json'
config      = load_config_file( config_file )

maestro     = maestro.Controller()

servo_init()

# servo_ready()

# servo_turn_x();
# servo_turn_x();
# servo_ready()

#servo_arm_test()
#servo_rail_test()

#servo_arm_left('BOTTOM');
#servo_arm_right('BOTTOM');

#servo_init()
#servo_init('rail')

maestro.close()
"""
