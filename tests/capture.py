import pygame
import pygame.camera
import time
import sys


def capture(filename):

	pygame.camera.init()
	pygame.camera.list_cameras()
	cam = pygame.camera.Camera('/dev/video0', (800, 600))
	cam.start()

	time.sleep(0.1)

	img = cam.get_image()
	pygame.image.save(img, './images/rubiks-side-' + filename + '.png')
	cam.stop()

capture( sys.argv[1] )
