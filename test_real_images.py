"""
Test CubeDetector on the original real cube photos.
"""
import cv2
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cube_detector import CubeDetector

FACE_ORDER = ['F', 'L', 'B', 'R', 'U', 'D']
image_dir = os.path.join('tests', 'images')
out_dir = os.path.join('tests', 'autodetect_real')
os.makedirs(out_dir, exist_ok=True)

detector = CubeDetector()

for face in FACE_ORDER:
    path = os.path.join(image_dir, f'rubiks-side-{face}.png')
    img_bgr = cv2.imread(path, cv2.IMREAD_COLOR)
    if img_bgr is None:
        print(f"  {face}: IMAGE NOT FOUND")
        continue
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h, w = img_rgb.shape[:2]
    print(f"\n=== Face {face} === ({w}x{h})")

    result = detector.detect_face_debug(img_rgb)

    # Save debug images
    cv2.imwrite(os.path.join(out_dir, f'{face}_orig.png'), img_bgr)
    if result.get('debug_img') is not None:
        cv2.imwrite(os.path.join(out_dir, f'{face}_detect.png'),
                    cv2.cvtColor(result['debug_img'], cv2.COLOR_RGB2BGR))
    if result.get('warped_debug') is not None:
        cv2.imwrite(os.path.join(out_dir, f'{face}_warped.png'),
                    cv2.cvtColor(result['warped_debug'], cv2.COLOR_RGB2BGR))
    if result.get('warped') is not None:
        cv2.imwrite(os.path.join(out_dir, f'{face}_warped_raw.png'),
                    cv2.cvtColor(result['warped'], cv2.COLOR_RGB2BGR))

    if not result['success']:
        print(f"  FAILED - no cube detected")
        continue

    colors = result['colors']
    print(f"  Corners: {result['corners']}")
    for row in range(3):
        for col in range(3):
            rgb = colors[row, col]
            print(f"  [{row},{col}] RGB=({rgb[0]:3d},{rgb[1]:3d},{rgb[2]:3d})", end="")
        print()

print(f"\nDebug images saved to {out_dir}/")
