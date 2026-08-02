"""
Test CubeDetector on synthetic and tilted cube images.
"""
import cv2
import numpy as np
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cube_detector import CubeDetector

# Standard Rubik's cube colors (RGB)
COLORS = {
    'U': (255, 255, 255),   # White
    'R': (183, 18, 52),     # Red
    'F': (0, 155, 72),      # Green
    'D': (255, 213, 0),     # Yellow
    'L': (255, 88, 0),      # Orange
    'B': (0, 70, 173),      # Blue
}

# Known valid kociemba state
STATE = "DRLUUBFBRBLURRLRUBLRDDFDLFUFUFFDBRDUBRUFLLFDDBFLUBLRBD"

# Face map: image name -> kociemba offset
FACE_MAP = {
    'F': 18, 'L': 9, 'B': 45, 'R': 36, 'U': 27, 'D': 0,
}

IMG_W, IMG_H = 640, 480
STICKER_SIZE = 80
GAP = 8
GRID_SIZE = STICKER_SIZE * 3 + GAP * 2

def make_cube_face(state, offset, tilt_deg=0, perspective=0, noise=0):
    """Generate a cube face image with optional tilt and perspective distortion."""
    # Create a larger canvas to allow for rotation
    canvas_size = max(IMG_W, IMG_H) + 200
    img = np.zeros((canvas_size, canvas_size, 3), dtype=np.uint8)

    # Draw 3x3 grid centered in canvas
    start_x = (canvas_size - GRID_SIZE) // 2
    start_y = (canvas_size - GRID_SIZE) // 2

    for row in range(3):
        for col in range(3):
            x = start_x + col * (STICKER_SIZE + GAP)
            y = start_y + row * (STICKER_SIZE + GAP)
            idx = offset + row * 3 + col
            color_char = STATE[idx]
            color_rgb = COLORS[color_char]
            # Add slight color variation per sticker
            variation = np.random.randint(-10, 10, 3)
            color = np.clip(np.array(color_rgb) + variation, 0, 255).astype(np.uint8)
            img[y:y+STICKER_SIZE, x:x+STICKER_SIZE] = (color[2], color[1], color[0])
            # Black gap between stickers
            cv2.rectangle(img, (x, y), (x+STICKER_SIZE, y+STICKER_SIZE), (15, 15, 15), 2)

    # Apply rotation
    if tilt_deg != 0:
        M = cv2.getRotationMatrix2D((canvas_size//2, canvas_size//2), tilt_deg, 1.0)
        img = cv2.warpAffine(img, M, (canvas_size, canvas_size))

    # Apply perspective distortion
    if perspective != 0:
        h, w = img.shape[:2]
        src = np.array([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]], dtype=np.float32)
        dst = src.copy()
        dst[0] = [perspective, perspective]
        dst[1] = [w-1-perspective, perspective*2]
        dst[2] = [w-1, h-1]
        dst[3] = [0, h-1]
        M = cv2.getPerspectiveTransform(src, dst)
        img = cv2.warpPerspective(img, M, (w, h))

    # Add noise
    if noise > 0:
        n = np.random.normal(0, noise, img.shape)
        img = np.clip(img.astype(float) + n, 0, 255).astype(np.uint8)

    # Crop to 640x480 centered
    cy, cx = canvas_size // 2, canvas_size // 2
    img = img[cy - IMG_H//2 : cy + IMG_H//2, cx - IMG_W//2 : cx + IMG_W//2]

    return img

def test_detection():
    detector = CubeDetector()

    test_cases = [
        ("perfect", 0, 0, 0),
        ("tilted_5", 5, 0, 0),
        ("tilted_15", 15, 0, 0),
        ("perspective", 0, 30, 0),
        ("tilt_persp", 8, 20, 0),
        ("noisy", 0, 0, 15),
        ("tilt_noisy", 10, 15, 12),
    ]

    out_dir = os.path.join('tests', 'autodetect')
    os.makedirs(out_dir, exist_ok=True)

    all_passed = True

    for face_name, offset in FACE_MAP.items():
        print(f"\n{'='*60}")
        print(f"Face: {face_name} (kociemba offset {offset})")
        print(f"{'='*60}")

        expected = []
        for row in range(3):
            for col in range(3):
                idx = offset + row * 3 + col
                expected.append(STATE[idx])
        expected_str = ' '.join(expected)
        print(f"Expected stickers: {expected_str}")

        for case_name, tilt, persp, noise in test_cases:
            np.random.seed(42 + offset)
            img_bgr = make_cube_face(STATE, offset, tilt, persp, noise)
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

            result = detector.detect_face_debug(img_rgb)

            # Save debug images
            cv2.imwrite(os.path.join(out_dir, f'{face_name}_{case_name}_orig.png'), img_bgr)
            if result.get('debug_img') is not None:
                cv2.imwrite(os.path.join(out_dir, f'{face_name}_{case_name}_detect.png'),
                           cv2.cvtColor(result['debug_img'], cv2.COLOR_RGB2BGR))
            if result.get('warped_debug') is not None:
                cv2.imwrite(os.path.join(out_dir, f'{face_name}_{case_name}_warped.png'),
                           cv2.cvtColor(result['warped_debug'], cv2.COLOR_RGB2BGR))

            if not result['success']:
                print(f"  [{case_name}] FAILED - no cube detected")
                all_passed = False
                continue

            # Check detected colors
            colors = result['colors']
            detected = []
            color_names = {
                (255, 255, 255): 'U',
                (183, 18, 52): 'R',
                (0, 155, 72): 'F',
                (255, 213, 0): 'D',
                (255, 88, 0): 'L',
                (0, 70, 173): 'B',
            }

            # Match detected colors to known colors
            matched = []
            for row in range(3):
                for col in range(3):
                    rgb = colors[row, col]
                    # Find nearest color
                    min_dist = float('inf')
                    best = '?'
                    for ref_rgb, name in color_names.items():
                        dist = sum((int(a) - int(b))**2 for a, b in zip(rgb, ref_rgb))
                        if dist < min_dist:
                            min_dist = dist
                            best = name
                    matched.append(best)

            detected_str = ' '.join(matched)
            correct = sum(1 for a, b in zip(expected, matched) if a == b)
            status = "OK" if correct == 9 else f"MISMATCH ({correct}/9)"
            if correct < 9:
                all_passed = False

            print(f"  [{case_name}] {status}")
            if correct < 9:
                print(f"    Expected: {expected_str}")
                print(f"    Detected: {detected_str}")
                # Show RGB values
                for row in range(3):
                    for col in range(3):
                        rgb = colors[row, col]
                        print(f"    [{row},{col}] RGB=({rgb[0]:3d},{rgb[1]:3d},{rgb[2]:3d}) -> {matched[row*3+col]}")

    print(f"\n{'='*60}")
    print(f"Overall: {'ALL PASSED' if all_passed else 'SOME FAILURES'}")
    print(f"Debug images saved to tests/autodetect/")
    return all_passed

if __name__ == '__main__':
    success = test_detection()
    sys.exit(0 if success else 1)
