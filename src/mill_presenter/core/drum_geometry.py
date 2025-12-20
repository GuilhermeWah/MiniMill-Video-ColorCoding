# MillPresenter Drum Geometry

"""
Drum detection, ROI generation, and calibration.
This module handles finding the mill drum in the frame and establishing
the Region of Interest (ROI) and pixel-to-millimeter calibration.
"""

import cv2
import numpy as np
from dataclasses import dataclass, asdict
from typing import Tuple, Dict, Any, Optional

from mill_presenter.core.models import DrumGeometry as DrumGeometryData
from mill_presenter.utils import config


class DrumGeometry:
    """
    Logic for drum detection and ROI management.
    Wraps the data model with behavioral methods.
    """
    
    def __init__(self, data: DrumGeometryData):
        self._data = data
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self._data.center_x, self._data.center_y)
    
    @property
    def radius(self) -> int:
        return self._data.radius_px
    
    @property
    def px_per_mm(self) -> float:
        return self._data.px_per_mm
    
    @classmethod
    def detect(cls, frame_bgr: np.ndarray, 
               drum_diameter_mm: float = 200.0) -> "DrumGeometry":
        """
        Auto-detect the drum in the frame using Hough Circles.
        
        Args:
            frame_bgr: Input frame (BGR).
            drum_diameter_mm: Physical diameter of the drum in mm.
            
        Returns:
            DrumGeometry instance.
            
        Raises:
            ValueError: If drum cannot be detected.
        """
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape[:2]
        min_dim = min(height, width)
        
        # Get config parameters
        min_ratio = config.get("drum_min_radius_ratio", 0.35)
        max_ratio = config.get("drum_max_radius_ratio", 0.48)
        dp = config.get("drum_hough_dp", 1)
        param1 = config.get("drum_hough_param1", 50)
        param2 = config.get("drum_hough_param2", 30)
        blur_k = config.get("drum_blur_ksize", 5)
        
        # Preprocessing for drum detection
        blurred = cv2.GaussianBlur(gray, (blur_k, blur_k), 0)
        
        min_radius = int(min_dim * min_ratio)
        max_radius = int(min_dim * max_ratio)
        
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=dp,
            minDist=min_dim,  # Expect only one drum
            param1=param1,
            param2=param2,
            minRadius=min_radius,
            maxRadius=max_radius
        )
        
        if circles is None:
            # Fallback: exact center of frame with conservative radius
            center_x, center_y = width // 2, height // 2
            radius = int(min_dim * 0.42)
            print("⚠ Drum detection failed. Using fallback geometry.")
        else:
            # Get the strongest circle (should be the only one)
            best_circle = circles[0][0]
            center_x = int(best_circle[0])
            center_y = int(best_circle[1])
            radius = int(best_circle[2])
        
        # Calculate calibration
        px_per_mm = radius / (drum_diameter_mm / 2)
        
        data = DrumGeometryData(
            center_x=center_x,
            center_y=center_y,
            radius_px=radius,
            px_per_mm=px_per_mm
        )
        
        return cls(data)
    
    def get_roi_mask(self, frame_shape: Tuple[int, int]) -> np.ndarray:
        """
        Generate a binary mask for the ROI (255 inside drum, 0 outside).
        
        Args:
            frame_shape: (height, width) of the target frame.
            
        Returns:
            Binary mask (uint8).
        """
        height, width = frame_shape[:2]
        mask = np.zeros((height, width), dtype=np.uint8)
        
        cv2.circle(
            mask, 
            (self._data.center_x, self._data.center_y), 
            self._data.radius_px, 
            255, 
            -1
        )
        
        return mask
    
    def get_inner_roi_mask(self, frame_shape: Tuple[int, int], 
                           margin_ratio: float = 0.12) -> np.ndarray:
        """
        Generate a mask with rim margin excluded.
        
        Args:
            frame_shape: (height, width)
            margin_ratio: Ratio of radius to exclude from the rim (default 0.12).
            
        Returns:
            Binary mask.
        """
        height, width = frame_shape[:2]
        mask = np.zeros((height, width), dtype=np.uint8)
        
        inner_radius = int(self._data.radius_px * (1.0 - margin_ratio))
        
        cv2.circle(
            mask, 
            (self._data.center_x, self._data.center_y), 
            inner_radius, 
            255, 
            -1
        )
        
        return mask
    
    def is_inside(self, x: int, y: int, margin_ratio: float = 0.0) -> bool:
        """
        Check if a point is inside the drum (optionally with margin).
        
        Args:
            x, y: Point coordinates.
            margin_ratio: Margin to exclude (0.0 = full drum).
            
        Returns:
            True if inside.
        """
        dx = x - self._data.center_x
        dy = y - self._data.center_y
        dist_sq = dx*dx + dy*dy
        
        radius = self._data.radius_px * (1.0 - margin_ratio)
        return dist_sq <= radius*radius
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize underlying data."""
        return self._data.to_dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DrumGeometry":
        """Deserialize from dictionary."""
        return cls(DrumGeometryData.from_dict(data))
    
    @property
    def model(self) -> DrumGeometryData:
        """Access underlying data model."""
        return self._data
