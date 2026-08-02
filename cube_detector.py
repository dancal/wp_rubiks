"""
Automatic Rubik's cube face detection module.
Detects the cube in an image, corrects perspective/skew,
and extracts colors from the 3x3 sticker grid.

Pipeline:
1. Detect cube boundaries using multiple methods:
   a. Grid line detection (projection profiles) - works when cube fills frame
   b. Contour detection (Otsu/HSV/Canny) - works with clear background
2. Apply perspective transform to get a square, axis-aligned face
3. Auto-crop to remove any remaining borders
4. Divide into 3x3 grid and extract center color of each sticker
"""

import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


class CubeDetector:
    """
    Detects a Rubik's cube face in an image and extracts 9 sticker colors.
    Handles tilted/skewed cubes via perspective correction.
    """

    FACE_SIZE = 360
    STICKER_SIZE = FACE_SIZE // 3

    def __init__(self, sticker_sample_ratio=0.4):
        self.sticker_sample_ratio = sticker_sample_ratio

    def detect_face(self, img):
        """
        Detect the cube face in an RGB image and extract 9 sticker colors.
        Tries both grid-line and contour detection, picks the better result.

        :param img: RGB image as numpy array (H, W, 3)
        :return: dict with 'colors', 'corners', 'warped', 'success'
        """
        if img is None or img.size == 0:
            return self._failure()

        h, w = img.shape[:2]

        # Try both detection methods and pick the best result
        candidates = []

        # Method 1: Grid line detection (brightness projection - works with black background)
        corners1 = self._find_corners_via_grid(img)
        if corners1 is not None and self._validate_corners(corners1, w, h):
            result1 = self._warp_and_extract(img, corners1)
            if result1['success']:
                result1['method'] = 'grid'
                candidates.append(result1)

        # Method 2: Contour detection (works with clear background)
        corners2 = self._find_corners_via_contours(img)
        if corners2 is not None and self._validate_corners(corners2, w, h):
            result2 = self._warp_and_extract(img, corners2)
            if result2['success']:
                result2['method'] = 'contour'
                candidates.append(result2)

        # Method 3: Grid line detection via blackhat (works when cube fills frame)
        corners3 = self._find_corners_via_grid_lines(img)
        if corners3 is not None and self._validate_corners(corners3, w, h):
            result3 = self._warp_and_extract(img, corners3)
            if result3['success']:
                result3['method'] = 'gridlines'
                candidates.append(result3)

        if not candidates:
            logger.warning('CubeDetector: no valid detection from any method')
            return self._failure()

        # Pick the best candidate: the one with highest color diversity
        # (a correct cube face should have multiple distinct colors)
        best = max(candidates, key=lambda r: self._color_diversity_score(r['colors']))
        best['method'] = best.get('method', 'unknown')
        logger.info(f'CubeDetector: selected {best["method"]} method (score={self._color_diversity_score(best["colors"]):.1f})')

        return best

    def _warp_and_extract(self, img, corners):
        """Warp perspective and extract colors from the given corners."""
        warped = self._warp_to_square(img, corners)
        warped = self._auto_crop_warped(warped)

        non_black = np.count_nonzero(np.any(warped > 15, axis=2))
        if non_black < warped.shape[0] * warped.shape[1] * 0.3:
            return self._failure()

        colors = self._extract_sticker_colors(warped)

        return {
            'colors': colors,
            'corners': corners,
            'warped': warped,
            'success': True,
        }

    def _color_diversity_score(self, colors):
        """
        Score a color extraction result based on how well colors match
        typical Rubik's cube sticker colors and how bright they are.
        Higher score = better.
        """
        # Typical Rubik's cube colors in RGB
        ref_colors = [
            np.array([255, 255, 255]),  # White
            np.array([255, 213, 0]),    # Yellow
            np.array([183, 18, 52]),    # Red
            np.array([255, 88, 0]),     # Orange
            np.array([0, 155, 72]),     # Green
            np.array([0, 70, 173]),     # Blue
        ]

        flat = colors.reshape(-1, 3).astype(np.float32)
        score = 0.0

        for c in flat:
            brightness = np.mean(c)
            if brightness < 20:
                # Dark/background pixel - penalize heavily
                score -= 50
                continue

            # Find distance to nearest reference color
            min_dist = min(np.linalg.norm(c - ref) for ref in ref_colors)
            # Closer to a known color = higher score
            # Max meaningful distance is ~200, so score = 200 - dist
            color_score = max(0, 200 - min_dist)
            score += color_score

        return score

    def _failure(self):
        return {
            'colors': np.zeros((3, 3, 3), dtype=np.uint8),
            'corners': None,
            'warped': None,
            'success': False,
        }

    # ------------------------------------------------------------------
    # Corner detection
    # ------------------------------------------------------------------

    def _find_cube_corners(self, img_rgb):
        """
        Find the four corners of the cube face.
        Tries grid-line detection first (robust for cube-filling-frame),
        then falls back to contour-based detection.
        """
        h, w = img_rgb.shape[:2]

        # Method 1: Grid line detection via projection profiles
        corners = self._find_corners_via_grid(img_rgb)
        if corners is not None and self._validate_corners(corners, w, h):
            logger.debug('CubeDetector: corners found via grid lines')
            return corners

        # Method 2: Contour-based detection
        corners = self._find_corners_via_contours(img_rgb)
        if corners is not None and self._validate_corners(corners, w, h):
            logger.debug('CubeDetector: corners found via contours')
            return corners

        return None

    def _find_corners_via_grid(self, img_rgb):
        """
        Detect cube boundaries using brightness projection.
        The cube is brighter than the black background.
        Returns a bounding-box quadrilateral.
        """
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape

        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        # Brightness projection
        h_brightness = np.mean(blurred, axis=1).astype(np.float32)
        v_brightness = np.mean(blurred, axis=0).astype(np.float32)

        # Smooth
        ks = max(h // 60, 3)
        if ks % 2 == 0:
            ks += 1
        h_brightness = cv2.GaussianBlur(h_brightness.reshape(1, -1), (ks, 1), 0).flatten()
        v_brightness = cv2.GaussianBlur(v_brightness.reshape(1, -1), (1, ks), 0).flatten()

        # Find cube boundaries using a fixed low threshold
        # Black background is ~0, darkest sticker (blue) is ~60 in grayscale
        h_thresh = 20
        v_thresh = 20

        y_positions = np.where(h_brightness > h_thresh)[0]
        if len(y_positions) == 0:
            return None
        y_top = int(y_positions[0])
        y_bottom = int(y_positions[-1])

        x_positions = np.where(v_brightness > v_thresh)[0]
        if len(x_positions) == 0:
            return None
        x_left = int(x_positions[0])
        x_right = int(x_positions[-1])

        # For tilted cubes, find the edge at each corner by sampling
        # brightness in strips near each corner
        sample_w = max((x_right - x_left) // 6, 15)

        # Sample y at left and right edges
        tl_y = self._find_brightness_edge_y(blurred, x_left + sample_w // 2, sample_w, 'top')
        tr_y = self._find_brightness_edge_y(blurred, x_right - sample_w // 2, sample_w, 'top')
        bl_y = self._find_brightness_edge_y(blurred, x_left + sample_w // 2, sample_w, 'bottom')
        br_y = self._find_brightness_edge_y(blurred, x_right - sample_w // 2, sample_w, 'bottom')

        # Sample x at top and bottom edges
        tl_x = self._find_brightness_edge_x(blurred, y_top + sample_w // 2, sample_w, 'left')
        tr_x = self._find_brightness_edge_x(blurred, y_top + sample_w // 2, sample_w, 'right')
        bl_x = self._find_brightness_edge_x(blurred, y_bottom - sample_w // 2, sample_w, 'left')
        br_x = self._find_brightness_edge_x(blurred, y_bottom - sample_w // 2, sample_w, 'right')

        corners = np.array([
            [tl_x, tl_y],
            [tr_x, tr_y],
            [br_x, br_y],
            [bl_x, bl_y],
        ], dtype=np.float32)

        return corners

    def _find_brightness_edge_y(self, gray, x_center, width, direction):
        """Find the y-position of the cube edge near a given x column using brightness."""
        h, w = gray.shape
        x0 = max(int(x_center - width // 2), 0)
        x1 = min(int(x_center + width // 2), w)
        if x1 <= x0:
            return float(y_center) if 'y_center' in dir() else 0.0

        strip = gray[:, x0:x1]
        col_mean = np.mean(strip, axis=1)

        # Use fixed threshold - black background is 0, darkest sticker is ~60
        threshold = 20

        if direction == 'top':
            for y in range(h):
                if col_mean[y] > threshold:
                    return float(y)
            return 0.0
        else:
            for y in range(h - 1, -1, -1):
                if col_mean[y] > threshold:
                    return float(y)
            return float(h - 1)

    def _find_brightness_edge_x(self, gray, y_center, width, direction):
        """Find the x-position of the cube edge near a given y row using brightness."""
        h, w = gray.shape
        y0 = max(int(y_center - width // 2), 0)
        y1 = min(int(y_center + width // 2), h)
        if y1 <= y0:
            return 0.0

        strip = gray[y0:y1, :]
        row_mean = np.mean(strip, axis=0)

        # Use fixed threshold
        threshold = 20

        if direction == 'left':
            for x in range(w):
                if row_mean[x] > threshold:
                    return float(x)
            return 0.0
        else:
            for x in range(w - 1, -1, -1):
                if row_mean[x] > threshold:
                    return float(x)
            return float(w - 1)

    def _find_corners_via_grid_lines(self, img_rgb):
        """
        Detect cube boundaries by finding dark grid lines between stickers.
        Grid lines appear as valleys (local minima) in the brightness profile.
        Uses large blur to smooth out sticker color variations.
        Works well when the cube fills the frame (no black background).
        """
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape

        # Blur to smooth sticker texture while preserving grid line dips
        # Use a moderate blur - too large smooths out grid lines
        blurred = cv2.GaussianBlur(gray, (11, 11), 0)

        # Row and column brightness profiles
        h_profile = np.mean(blurred, axis=1).astype(np.float32)
        v_profile = np.mean(blurred, axis=0).astype(np.float32)

        # Find valleys (grid lines = local minima)
        h_lines = self._find_valleys(h_profile, h)
        v_lines = self._find_valleys(v_profile, w)

        if h_lines is None or v_lines is None:
            return None
        if len(h_lines) < 2 or len(v_lines) < 2:
            return None

        # Use outermost grid lines as cube boundaries
        y_top = h_lines[0]
        y_bottom = h_lines[-1]
        x_left = v_lines[0]
        x_right = v_lines[-1]

        # For tilted cubes, refine corners by sampling at edges
        sample_w = max((x_right - x_left) // 6, 15)

        tl_y = self._find_brightness_edge_y(blurred, x_left + sample_w // 2, sample_w, 'top')
        tr_y = self._find_brightness_edge_y(blurred, x_right - sample_w // 2, sample_w, 'top')
        bl_y = self._find_brightness_edge_y(blurred, x_left + sample_w // 2, sample_w, 'bottom')
        br_y = self._find_brightness_edge_y(blurred, x_right - sample_w // 2, sample_w, 'bottom')

        tl_x = self._find_brightness_edge_x(blurred, y_top + sample_w // 2, sample_w, 'left')
        tr_x = self._find_brightness_edge_x(blurred, y_top + sample_w // 2, sample_w, 'right')
        bl_x = self._find_brightness_edge_x(blurred, y_bottom - sample_w // 2, sample_w, 'left')
        br_x = self._find_brightness_edge_x(blurred, y_bottom - sample_w // 2, sample_w, 'right')

        corners = np.array([
            [tl_x, tl_y],
            [tr_x, tr_y],
            [br_x, br_y],
            [bl_x, bl_y],
        ], dtype=np.float32)

        return corners

    def _find_valleys(self, profile, size):
        """
        Find valleys (local minima) in a brightness profile.
        Grid lines between stickers appear as dips in brightness.
        Returns sorted list of valley positions, or None.
        """
        if len(profile) == 0:
            return None

        # Smooth the profile with a larger kernel to reduce noise
        ks = max(size // 40, 5)
        if ks % 2 == 0:
            ks += 1
        smoothed = cv2.GaussianBlur(
            profile.reshape(1, -1).astype(np.float32), (ks, 1), 0
        ).flatten()

        mean_val = np.mean(smoothed)
        std_val = np.std(smoothed)
        # Valleys are below mean - they're darker than average
        # Use a small offset since grid line dips can be subtle
        threshold = mean_val - 0.05 * std_val

        min_distance = size // 12

        # Find regions where profile drops below threshold
        valleys = []
        i = 0
        while i < len(smoothed):
            if smoothed[i] < threshold:
                j = i
                while j < len(smoothed) and smoothed[j] < threshold:
                    j += 1
                # Valley center is the minimum position
                valley_pos = i + int(np.argmin(smoothed[i:j]))
                valleys.append(valley_pos)
                i = j + min_distance
            else:
                i += 1

        if len(valleys) < 2:
            return None

        # Merge close valleys
        merged = [valleys[0]]
        for p in valleys[1:]:
            if p - merged[-1] >= min_distance:
                merged.append(p)
            else:
                if smoothed[p] < smoothed[merged[-1]]:
                    merged[-1] = p

        return sorted(merged) if len(merged) >= 2 else None

    def _find_corners_via_contours(self, img_rgb):
        """
        Find cube corners using contour detection on thresholded images.
        Works well when there's a clear background behind the cube.
        """
        h, w = img_rgb.shape[:2]
        min_area = (w * h) * 0.05
        max_area = (w * h) * 0.90

        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))

        masks = []

        # Otsu thresholding
        _, otsu_mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        otsu_mask = cv2.morphologyEx(otsu_mask, cv2.MORPH_CLOSE, kernel)
        otsu_mask = cv2.dilate(otsu_mask, kernel, iterations=3)
        masks.append(('otsu', otsu_mask))

        # HSV saturation + value
        hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
        sat_mask = cv2.inRange(hsv[:, :, 1], 20, 255)
        val_mask = cv2.inRange(hsv[:, :, 2], 80, 255)
        hsv_mask = cv2.bitwise_or(sat_mask, val_mask)
        hsv_mask = cv2.morphologyEx(hsv_mask, cv2.MORPH_CLOSE, kernel)
        hsv_mask = cv2.morphologyEx(hsv_mask, cv2.MORPH_OPEN, kernel)
        hsv_mask = cv2.dilate(hsv_mask, kernel, iterations=4)
        masks.append(('hsv', hsv_mask))

        # Canny edges
        edges = cv2.Canny(blurred, 30, 120)
        edges = cv2.dilate(edges, kernel, iterations=2)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        masks.append(('canny', edges))

        for method_name, mask in masks:
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if not contours:
                continue

            contours = sorted(contours, key=cv2.contourArea, reverse=True)

            for contour in contours[:10]:
                area = cv2.contourArea(contour)
                if area < min_area or area > max_area:
                    continue

                corners = self._extract_quad(contour)
                if corners is None:
                    continue

                if self._validate_corners(corners, w, h):
                    return corners

        return None

    # ------------------------------------------------------------------
    # Validation and geometry
    # ------------------------------------------------------------------

    def _validate_corners(self, corners, img_w, img_h):
        """Check that corners form a reasonable quadrilateral for a cube face."""
        margin = 10
        for x, y in corners:
            if x < -margin or x > img_w + margin or y < -margin or y > img_h + margin:
                return False

        tl, tr, br, bl = corners
        width_top = np.linalg.norm(tr - tl)
        width_bottom = np.linalg.norm(br - bl)
        height_left = np.linalg.norm(bl - tl)
        height_right = np.linalg.norm(br - tr)

        min_side = 50
        if width_top < min_side or width_bottom < min_side:
            return False
        if height_left < min_side or height_right < min_side:
            return False

        max_dim = max(width_top, width_bottom, height_left, height_right)
        min_dim = min(width_top, width_bottom, height_left, height_right)
        if min_dim / max_dim < 0.3:
            return False

        return True

    def _extract_quad(self, contour):
        """Extract a quadrilateral from a contour."""
        peri = cv2.arcLength(contour, True)

        for eps in [0.02, 0.04, 0.06, 0.08, 0.1]:
            approx = cv2.approxPolyDP(contour, eps * peri, True)
            if len(approx) == 4:
                return self._order_corners(approx.reshape(4, 2).astype(np.float32))

        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect)
        return self._order_corners(box.astype(np.float32))

    @staticmethod
    def _order_corners(pts):
        """Order corners as: Top-Left, Top-Right, Bottom-Right, Bottom-Left."""
        rect = np.zeros((4, 2), dtype=np.float32)

        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        d = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(d)]
        rect[3] = pts[np.argmax(d)]

        return rect

    # ------------------------------------------------------------------
    # Perspective transform and color extraction
    # ------------------------------------------------------------------

    def _warp_to_square(self, img, corners):
        """Apply perspective transform to get a square, axis-aligned face image."""
        dst = np.array([
            [0, 0],
            [self.FACE_SIZE - 1, 0],
            [self.FACE_SIZE - 1, self.FACE_SIZE - 1],
            [0, self.FACE_SIZE - 1],
        ], dtype=np.float32)

        matrix = cv2.getPerspectiveTransform(corners, dst)
        warped = cv2.warpPerspective(img, matrix, (self.FACE_SIZE, self.FACE_SIZE))
        return warped

    def _auto_crop_warped(self, warped):
        """
        Crop the warped image to the actual cube area by finding the
        bounding box of non-black pixels. Always crop to ensure
        the 3x3 grid aligns with the cube content.
        """
        gray = cv2.cvtColor(warped, cv2.COLOR_RGB2GRAY)
        _, mask = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY)

        coords = cv2.findNonZero(mask)
        if coords is None:
            return warped

        x, y, w, h = cv2.boundingRect(coords)

        # Add a small margin to avoid cutting off sticker edges
        margin = 2
        x = max(x - margin, 0)
        y = max(y - margin, 0)
        w = min(w + 2 * margin, warped.shape[1] - x)
        h = min(h + 2 * margin, warped.shape[0] - y)

        # Always crop and resize
        cropped = warped[y:y+h, x:x+w]
        if cropped.size == 0:
            return warped

        warped = cv2.resize(cropped, (self.FACE_SIZE, self.FACE_SIZE),
                            interpolation=cv2.INTER_AREA)

        return warped

    def _extract_sticker_colors(self, warped):
        """Extract the center color of each of the 9 stickers (uniform grid)."""
        colors = np.zeros((3, 3, 3), dtype=np.uint8)
        s = self.STICKER_SIZE
        ratio = self.sticker_sample_ratio
        margin = int(s * (1 - ratio) / 2)

        for row in range(3):
            for col in range(3):
                x0 = col * s + margin
                y0 = row * s + margin
                x1 = (col + 1) * s - margin
                y1 = (row + 1) * s - margin

                cell = warped[y0:y1, x0:x1]
                if cell.size == 0:
                    continue

                median_color = np.median(cell.reshape(-1, 3), axis=0)
                colors[row, col, :] = np.clip(median_color, 0, 255).astype(np.uint8)

        return colors

    def _refine_grid_in_warped(self, warped):
        """
        Detect grid lines within the warped image to find exact sticker boundaries.
        Returns (h_lines, v_lines) - lists of 4 y/x positions defining the grid.
        Falls back to uniform grid if detection fails.
        """
        gray = cv2.cvtColor(warped, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape
        s = self.STICKER_SIZE

        # Default: uniform grid
        default_h = [0, s, 2 * s, 3 * s]
        default_v = [0, s, 2 * s, 3 * s]

        # Use morphological blackhat to find dark grid lines
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 10, 20), 3))
        blackhat_h = cv2.morphologyEx(blurred, cv2.MORPH_BLACKHAT, h_kernel)

        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, max(h // 10, 20)))
        blackhat_v = cv2.morphologyEx(blurred, cv2.MORPH_BLACKHAT, v_kernel)

        # Projection profiles
        h_proj = np.sum(blackhat_h, axis=1).astype(np.float32)
        v_proj = np.sum(blackhat_v, axis=0).astype(np.float32)

        # Find grid lines - expect 4 lines (2 borders + 2 internal)
        h_lines = self._find_grid_lines_detailed(h_proj, h, s)
        v_lines = self._find_grid_lines_detailed(v_proj, w, s)

        if h_lines is None:
            h_lines = default_h
        if v_lines is None:
            v_lines = default_v

        # Ensure we have exactly 4 lines
        if len(h_lines) < 4:
            h_lines = default_h
        if len(v_lines) < 4:
            v_lines = default_v

        # Take first 4 and ensure they're sorted
        h_lines = sorted(h_lines[:4])
        v_lines = sorted(v_lines[:4])

        # Validate: grid lines should be roughly evenly spaced
        h_lines = self._validate_grid_spacing(h_lines, default_h)
        v_lines = self._validate_grid_spacing(v_lines, default_v)

        return (h_lines, v_lines)

    def _validate_grid_spacing(self, lines, default):
        """
        Check that grid lines are roughly evenly spaced and span most of the image.
        Only use refined grid if it differs significantly from uniform (real images)
        but is still valid. For synthetic images with perfect alignment, uniform is better.
        """
        if len(lines) != 4:
            return default

        gaps = [lines[i+1] - lines[i] for i in range(3)]
        if min(gaps) <= 0:
            return default

        mean_gap = np.mean(gaps)
        for g in gaps:
            if g < mean_gap * 0.4 or g > mean_gap * 1.6:
                return default

        # Total span should be at least 50% of the default span
        total_span = lines[-1] - lines[0]
        default_span = default[-1] - default[0]
        if total_span < default_span * 0.5:
            return default

        # Check if refined grid is significantly different from uniform
        # If the difference is small (< 15% of sticker size), use uniform (more stable)
        max_diff = max(abs(lines[i] - default[i]) for i in range(4))
        if max_diff < self.STICKER_SIZE * 0.15:
            return default

        return lines

    def _find_grid_lines_detailed(self, projection, size, sticker_size):
        """
        Find all grid lines (including borders) from a projection profile.
        Expect 4 lines: 2 borders + 2 internal grid lines.
        """
        if len(projection) == 0:
            return None

        # Smooth
        kernel_size = max(size // 80, 3)
        if kernel_size % 2 == 0:
            kernel_size += 1
        smoothed = cv2.GaussianBlur(
            projection.reshape(1, -1).astype(np.float32),
            (kernel_size, 1), 0
        ).flatten()

        mean_val = np.mean(smoothed)
        std_val = np.std(smoothed)
        threshold = mean_val + 0.3 * std_val

        # Find all peaks
        peaks = []
        min_distance = sticker_size // 3
        i = 0
        while i < len(smoothed):
            if smoothed[i] > threshold:
                j = i
                while j < len(smoothed) and smoothed[j] > threshold:
                    j += 1
                peak_pos = i + int(np.argmax(smoothed[i:j]))
                peaks.append(peak_pos)
                i = j + min_distance
            else:
                i += 1

        # Merge close peaks
        merged = []
        for p in peaks:
            if not merged or p - merged[-1] >= min_distance:
                merged.append(p)
            else:
                if smoothed[p] > smoothed[merged[-1]]:
                    merged[-1] = p

        if len(merged) < 2:
            return None

        # If we found exactly 4, great
        # If we found 2 (just the borders), add interpolated internal lines
        # If we found 3, add one more
        if len(merged) >= 4:
            return merged[:4]

        if len(merged) == 2:
            # Interpolate 2 internal lines
            start, end = merged[0], merged[1]
            gap = (end - start) / 3
            return [start, int(start + gap), int(start + 2 * gap), end]

        if len(merged) == 3:
            # Find which internal line is missing
            start, mid, end = merged
            gap1 = mid - start
            gap2 = end - mid
            if gap1 > gap2 * 1.5:
                # Missing line between start and mid
                return [start, int(start + gap1 / 2), mid, end]
            else:
                # Missing line between mid and end
                return [start, mid, int(mid + gap2 / 2), end]

        return merged

    def _extract_sticker_colors_refined(self, warped, grid_bounds):
        """
        Extract sticker colors using refined grid boundaries.
        grid_bounds = (h_lines, v_lines) where each is a list of 4 positions.
        """
        colors = np.zeros((3, 3, 3), dtype=np.uint8)
        h_lines, v_lines = grid_bounds
        ratio = self.sticker_sample_ratio

        for row in range(3):
            for col in range(3):
                # Cell boundaries from refined grid
                x_start = int(v_lines[col])
                x_end = int(v_lines[col + 1])
                y_start = int(h_lines[row])
                y_end = int(h_lines[row + 1])

                # Apply sample ratio margin
                cell_w = x_end - x_start
                cell_h = y_end - y_start
                margin_x = int(cell_w * (1 - ratio) / 2)
                margin_y = int(cell_h * (1 - ratio) / 2)

                x0 = x_start + margin_x
                y0 = y_start + margin_y
                x1 = x_end - margin_x
                y1 = y_end - margin_y

                if x1 <= x0 or y1 <= y0:
                    continue

                cell = warped[y0:y1, x0:x1]
                if cell.size == 0:
                    continue

                median_color = np.median(cell.reshape(-1, 3), axis=0)
                colors[row, col, :] = np.clip(median_color, 0, 255).astype(np.uint8)

        return colors

    # ------------------------------------------------------------------
    # Debug visualization
    # ------------------------------------------------------------------

    def detect_face_debug(self, img):
        """Same as detect_face but returns additional debug visualization."""
        result = self.detect_face(img)

        debug_img = img.copy()
        if result['corners'] is not None:
            corners = result['corners'].astype(int)
            for i, (x, y) in enumerate(corners):
                cv2.circle(debug_img, (x, y), 8, (0, 255, 0), -1)
                cv2.putText(debug_img, str(i), (x + 10, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.polylines(debug_img, [corners.reshape(-1, 1, 2)],
                          True, (255, 0, 0), 3)

        if result['warped'] is not None:
            warped_debug = result['warped'].copy()
            # Draw refined grid lines
            h_lines, v_lines = self._refine_grid_in_warped(result['warped'])
            for y in h_lines:
                cv2.line(warped_debug, (0, int(y)), (self.FACE_SIZE, int(y)),
                         (0, 255, 0), 2)
            for x in v_lines:
                cv2.line(warped_debug, (int(x), 0), (int(x), self.FACE_SIZE),
                         (0, 255, 0), 2)
            result['warped_debug'] = warped_debug

        result['debug_img'] = debug_img
        return result
