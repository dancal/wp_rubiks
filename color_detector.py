"""
Improved Color Detection and Calibration Module
Addresses color recognition errors in Rubik's cube solving
"""

import numpy as np
import cv2
from scipy.spatial import distance
from sklearn.cluster import KMeans
import logging

logger = logging.getLogger(__name__)

class ColorCalibrator:
    """
    Handles color calibration and runtime adaptation.
    Uses the center stickers of each face for automatic color reference generation.
    """
    
    def __init__(self):
        self.reference_colors_lab = None
        self.reference_colors_rgb = None
        self.is_calibrated = False
        
    def calibrate_from_centers(self, all_face_colors):
        """
        Calibrate color references using center stickers from all 6 faces.
        
        :param all_face_colors: List of 6 (3x3x3) color patches (one per face)
        :return: True if calibration successful
        """
        try:
            center_colors_rgb = []
            
            # Extract center sticker (index 4) from each face (URFDLB order)
            for face_idx in range(6):
                face_3x3 = all_face_colors[face_idx]
                center_color = face_3x3[1, 1, :]  # Center of 3x3 grid
                center_colors_rgb.append(center_color)
            
            # Convert to LAB color space
            center_colors_rgb = np.array(center_colors_rgb, dtype=np.uint8)
            self.reference_colors_rgb = center_colors_rgb
            self.reference_colors_lab = self._rgb_to_lab_array(center_colors_rgb)
            self.is_calibrated = True
            
            logger.info(f"Color calibration successful. Reference colors (RGB): {center_colors_rgb}")
            return True
            
        except Exception as e:
            logger.error(f"Color calibration failed: {e}")
            return False
    
    @staticmethod
    def _rgb_to_lab_array(rgb_array):
        """Convert RGB array to LAB color space."""
        rgb_array = np.asarray(rgb_array, dtype=np.uint8)
        lab = cv2.cvtColor(rgb_array.reshape(-1, 1, 3), cv2.COLOR_RGB2LAB)
        return lab.reshape(-1, 3).astype(np.float32)
    
    @staticmethod
    def _rgb_to_lab(rgb):
        """Convert single RGB color to LAB."""
        rgb_arr = np.asarray(rgb, dtype=np.float32)
        rgb_arr = np.clip(rgb_arr, 0, 255).astype(np.uint8)
        lab = cv2.cvtColor(rgb_arr.reshape(1, 1, 3), cv2.COLOR_RGB2LAB)
        return lab.reshape(3).astype(np.float32)


class ColorMatcher:
    """
    Matches detected colors to reference colors using LAB color space.
    More robust to lighting variations than RGB.
    """
    
    @staticmethod
    def match_sticker_colors(face_colors_rgb, reference_colors_rgb):
        """
        Match 9 sticker colors to 6 reference colors.
        
        :param face_colors_rgb: (3, 3, 3) array of sticker RGB values
        :param reference_colors_rgb: (6, 3) array of reference RGB values
        :return: (3, 3) array of matched color indices (0-5)
        """
        if reference_colors_rgb is None:
            logger.warning("No reference colors provided, using placeholder")
            return np.zeros((3, 3), dtype=int)
        
        try:
            # Convert to LAB space
            face_lab = ColorCalibrator._rgb_to_lab_array(face_colors_rgb.reshape(9, 3))
            reference_lab = ColorCalibrator._rgb_to_lab_array(reference_colors_rgb)
            
            # Find nearest reference color for each sticker
            d = distance.cdist(face_lab, reference_lab, metric='euclidean')
            matched_indices = np.argmin(d, axis=1)
            
            # Reshape to 3x3 grid
            return matched_indices.reshape(3, 3)
            
        except Exception as e:
            logger.error(f"Color matching failed: {e}")
            return np.zeros((3, 3), dtype=int)
    
    @staticmethod
    def improve_color_consistency(face_colors_rgb, matched_indices):
        """
        Improve consistency by replacing sticker colors with mean of matched group.
        
        :param face_colors_rgb: Original (3, 3, 3) sticker colors
        :param matched_indices: (3, 3) matched color indices
        :return: (3, 3, 3) corrected sticker colors
        """
        corrected = face_colors_rgb.copy()
        
        try:
            for color_idx in range(6):
                mask = matched_indices == color_idx
                if np.any(mask):
                    mean_color = np.mean(face_colors_rgb[mask], axis=0)
                    corrected[mask] = mean_color
        except Exception as e:
            logger.warning(f"Color consistency improvement failed: {e}")
        
        return corrected.astype(np.uint8)


class ImageProcessor:
    """
    Enhanced image preprocessing for better color extraction.
    """
    
    @staticmethod
    def preprocess_image(img, apply_clahe=True, apply_bilateral=True):
        """
        Preprocess captured image for better color detection.
        
        :param img: Input BGR image
        :param apply_clahe: Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        :param apply_bilateral: Apply bilateral filter
        :return: Preprocessed RGB image
        """
        try:
            # Convert BGR to RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Apply bilateral filter to reduce noise while preserving edges
            if apply_bilateral:
                img_rgb = cv2.bilateralFilter(img_rgb, 9, 75, 75)
            
            # Apply CLAHE to improve contrast
            if apply_clahe:
                # Convert to LAB, apply CLAHE to L channel
                img_lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
                l_channel = img_lab[:, :, 0]
                
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                l_channel = clahe.apply(l_channel)
                img_lab[:, :, 0] = l_channel
                
                img_rgb = cv2.cvtColor(img_lab, cv2.COLOR_LAB2RGB)
            
            return img_rgb
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}")
            return img_rgb if 'img_rgb' in locals() else img


class StabilityChecker:
    """
    Checks color detection stability across multiple captures.
    """
    
    def __init__(self, num_samples=3):
        self.num_samples = num_samples
        self.previous_colors = []
    
    def check_stability(self, current_colors):
        """
        Check if current detection is stable compared to previous ones.
        
        :param current_colors: Current detected colors
        :return: Stability score (0-1), 1 = most stable
        """
        if not self.previous_colors:
            self.previous_colors.append(current_colors)
            return 1.0
        
        try:
            # Calculate distance to previous detections
            distances = []
            for prev_color in self.previous_colors:
                dist = np.mean(np.abs(current_colors - prev_color) / 255.0)
                distances.append(dist)
            
            # Average distance (lower is better, more stable)
            avg_distance = np.mean(distances)
            stability = 1.0 - np.clip(avg_distance, 0, 1)
            
            # Keep buffer of recent detections
            self.previous_colors.append(current_colors)
            if len(self.previous_colors) > self.num_samples:
                self.previous_colors.pop(0)
            
            return stability
            
        except Exception as e:
            logger.warning(f"Stability check failed: {e}")
            return 0.5
    
    def reset(self):
        """Reset history for new capture session."""
        self.previous_colors = []


# Color definitions for reference
COLOR_NAMES = {
    0: 'White',
    1: 'Green', 
    2: 'Blue',
    3: 'Red',
    4: 'Yellow',
    5: 'Orange'
}

def get_color_name(color_idx):
    """Get human-readable color name."""
    return COLOR_NAMES.get(color_idx, 'Unknown')
