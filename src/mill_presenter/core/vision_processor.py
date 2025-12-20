# MillPresenter Vision Processor

"""
Dual-path circle detection using HoughCircles and Contour analysis.
This is the core detection module that generates raw circle candidates.

Legacy nomenclature: VisionProcessor
"""

import cv2
import numpy as np
import math
from typing import List, Tuple, Optional
from dataclasses import dataclass

from mill_presenter.core.models import RawDetection
from mill_presenter.core.drum_geometry import DrumGeometry
from mill_presenter.utils import config


class VisionProcessor:
    """
    Dual-path circle detector combining HoughCircles and Contour analysis.
    
    Path A: HoughCircles - good for clear, well-defined circles
    Path B: Contour analysis - catches partial/blurred circles
    
    Both paths produce candidates that are merged and filtered downstream.
    """
    
    def __init__(self, cfg: Optional[dict] = None):
        """
        Initialize the vision processor.
        
        Args:
            cfg: Optional config override.
        """
        self._cfg = cfg or config.CONFIG
    
    def detect(self, preprocessed: np.ndarray, 
               geometry: DrumGeometry) -> List[RawDetection]:
        """
        Run dual-path detection on preprocessed image.
        
        Args:
            preprocessed: Grayscale preprocessed image.
            geometry: Drum geometry for radius constraints.
            
        Returns:
            List of raw detections from both paths.
        """
        # Calculate radius bounds in pixels
        min_radius, max_radius = self._get_radius_bounds(geometry)
        
        # Path A: HoughCircles
        hough_candidates = self._detect_hough(preprocessed, min_radius, max_radius)
        
        # Path B: Contour analysis
        contour_candidates = self._detect_contours(preprocessed, min_radius, max_radius)
        
        # Merge candidates
        all_candidates = hough_candidates + contour_candidates
        
        return all_candidates
    
    def _get_radius_bounds(self, geometry: DrumGeometry) -> Tuple[int, int]:
        """Calculate min/max radius in pixels for bead detection."""
        px_per_mm = geometry.px_per_mm
        
        min_mm = self._cfg.get("min_bead_diameter_mm", 3.0) / 2.0
        max_mm = self._cfg.get("max_bead_diameter_mm", 12.0) / 2.0
        
        margin_low = self._cfg.get("radius_margin_low", 0.7)
        margin_high = self._cfg.get("radius_margin_high", 1.5)
        
        min_radius = int(min_mm * px_per_mm * margin_low)
        max_radius = int(max_mm * px_per_mm * margin_high)
        
        # Ensure minimum of 3 pixels
        min_radius = max(3, min_radius)
        
        return min_radius, max_radius
    
    def _detect_hough(self, gray: np.ndarray, 
                      min_radius: int, max_radius: int) -> List[RawDetection]:
        """
        Path A: HoughCircles detection.
        
        Uses resolution-adaptive param2 for better performance on 4K.
        """
        height = gray.shape[0]
        
        dp = self._cfg.get("hough_dp", 1)
        param1 = self._cfg.get("hough_param1", 50)
        param2_base = self._cfg.get("hough_param2_base", 25)
        min_dist_ratio = self._cfg.get("hough_min_dist_ratio", 0.5)
        
        # Resolution-adaptive param2
        param2 = max(param2_base, int(param2_base * math.sqrt(height / 1080)))
        
        min_dist = int(min_radius * min_dist_ratio)
        min_dist = max(1, min_dist)
        
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=dp,
            minDist=min_dist,
            param1=param1,
            param2=param2,
            minRadius=min_radius,
            maxRadius=max_radius
        )
        
        detections = []
        if circles is not None:
            for circle in circles[0]:
                x, y, r = circle
                detections.append(RawDetection(
                    x=int(x),
                    y=int(y),
                    r_px=float(r),
                    source="hough"
                ))
        
        return detections
    
    def _detect_contours(self, gray: np.ndarray,
                         min_radius: int, max_radius: int) -> List[RawDetection]:
        """
        Path B: Contour-based circle detection.
        
        Uses Canny edge detection, morphological operations, and circularity filtering.
        Catches circles that HoughCircles may miss (blurred, partial, irregular edges).
        """
        min_circularity = self._cfg.get("contour_min_circularity", 0.65)
        
        # Adaptive Canny thresholds using Otsu
        otsu_thresh, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        low_thresh = max(10, int(otsu_thresh * 0.5))
        high_thresh = int(otsu_thresh)
        
        edges = cv2.Canny(gray, low_thresh, high_thresh)
        
        # Morphological close to connect broken edges
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 10:  # Skip tiny contours
                continue
            
            perimeter = cv2.arcLength(contour, True)
            if perimeter == 0:
                continue
            
            # Circularity = 4π × area / perimeter²
            circularity = 4 * math.pi * area / (perimeter ** 2)
            
            if circularity < min_circularity:
                continue
            
            # Get enclosing circle
            (x, y), radius = cv2.minEnclosingCircle(contour)
            
            # Apply radius constraints
            if radius < min_radius or radius > max_radius:
                continue
            
            detections.append(RawDetection(
                x=int(x),
                y=int(y),
                r_px=float(radius),
                source="contour"
            ))
        
        return detections
