#!/usr/bin/env python
#
# This is the Python library for controlling the PivotPi (https://www.dexterindustries.com/Pivotpi/)

import maestro

SERVO_1 = 0
SERVO_2 = 1
SERVO_3 = 2
SERVO_4 = 3
SERVO_5 = 4
SERVO_6 = 5
SERVO_7 = 6
SERVO_8 = 7

#map 0-180 to pulse length between 150-600
def translate(value, leftMin, leftMax, rightMin, rightMax):
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (float)
    valueScaled = float(value - leftMin) / float(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return int(rightMin + (valueScaled * rightSpan))

class PivotPi(object):

    servo_controller=None
    # Configure min and max servo pulse lengths
    servo_min = 990   # Min pulse length out of 4096
    servo_max = 8000  # Max pulse length out of 4096
    frequency = 60;

    def __init__(self, actual_frequency = 110):
        try:
            self.servo_controller 	= maestro.Controller()
            self.frequency 			= actual_frequency;
            for i in range(7):
                self.servo_controller.setAccel( i, actual_frequency )
                    
            # Set frequency to 60hz, good for servos.
        except:
            # pass
            raise IOError("PivotPi not connected")
        return
    
    def pwm(self, channel, on, off):
        print("pwd")
        #try:
        #    self.servo_controller.set_pwm(channel, on, off)
        #except:
        #    raise IOError("PivotPi not connected")
    
    def angle(self, channel, angle):
        #pwm_to_send = 4095 - translate(angle, 0, 180, self.servo_min, self.servo_max)
        #pwm_to_send = translate(angle, 0, 90, self.servo_min, self.servo_max)
        # self.servo_controller.setTarget(channel, int(pwm_to_send))
        try:
            if angle >= 0 and channel >= 0 and channel <= 7:
                #print("angle = ", int(angle))
                self.servo_controller.setTarget( channel, int(angle) )
                return 1

        except:
            raise IOError("PivotPi not connected")
        return -1

