"""
Drum geometry and ROI mask generation module.

STEP_01: Drum Geometry & ROI Stabilization

This module implements:
- Binary ROI mask generation
- Visualization overlay
- Geometry validation

Values are in pixel space only.
"""

import cv2
import numpy as np
from typing import Tuple

from .config import DrumGeometry


def imwrite_unicode(path: str, image: np.ndarray) -> bool:
    """
    Write an image to a file path that may contain Unicode characters.
    
    OpenCV's cv2.imwrite() fails with Unicode paths on Windows.
    This function uses cv2.imencode + Python file I/O as a workaround.
    
    Args:
        path: Output file path (may contain Unicode characters).
        image: Image array to write.
        
    Returns:
        True if successful, False otherwise.
    """
    try:
        # Determine extension
        ext = path.rsplit('.', 1)[-1].lower()
        if ext not in ('png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif'):
            ext = 'png'
        
        # Encode image to bytes
        success, encoded = cv2.imencode(f'.{ext}', image)
        if not success:
            return False
        
        # Write bytes using Python's file I/O (handles Unicode)
        with open(path, 'wb') as f:
            f.write(encoded.tobytes())
        
        return True
    except Exception:
        return False

def generate_roi_mask(
    geometry: DrumGeometry,
    frame_shape: Tuple[int, int]
) -> np.ndarray:
    """
    Generate a binary ROI mask.
    White (255) = active process area.
    Black (0) = excluded (outside drum or in rim margin).
    """
    height, width = frame_shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)
    
    center = (geometry.drum_center_x_px, geometry.drum_center_y_px)
    # Effective radius is the inner boundary of the grindable area
    effective_radius = geometry.effective_radius_px
    
    if effective_radius > 0:
        cv2.circle(
            mask,
            center=center,
            radius=effective_radius,
            color=255,
            thickness=-1
        )
    
    return mask

def create_geometry_overlay(
    frame: np.ndarray,
    geometry: DrumGeometry
) -> np.ndarray:
    """
    Create a visualization overlay showing:
    - Full drum radius (Cyan)
    - Effective ROI radius (Green)
    - Excluded rim region (Red tint)
    """
    overlay = frame.copy()
    output = frame.copy()
    
    center = (geometry.drum_center_x_px, geometry.drum_center_y_px)
    full_radius = geometry.drum_radius_px
    effective_radius = geometry.effective_radius_px
    
    # Colors (BGR)
    CYAN = (255, 255, 0)
    GREEN = (0, 255, 0)
    RED = (0, 0, 255)
    
    # 1. Highlight excluded rim band
    rim_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    cv2.circle(rim_mask, center, full_radius, 255, -1)
    cv2.circle(rim_mask, center, effective_radius, 0, -1)
    
    # Apply red tint to rim
    overlay[rim_mask > 0] = (
        overlay[rim_mask > 0] * 0.6 + 
        np.array(RED, dtype=np.float32) * 0.4
    ).astype(np.uint8)
    
    # 2. Draw circles
    cv2.circle(overlay, center, full_radius, CYAN, 2)
    cv2.circle(overlay, center, effective_radius, GREEN, 2)
    
    # 3. Draw Center
    cv2.drawMarker(overlay, center, (255, 255, 255), cv2.MARKER_CROSS, 20, 2)
    
    # Blend
    cv2.addWeighted(overlay, 0.7, output, 0.3, 0, output)
    
    return output

def validate_geometry(
    geometry: DrumGeometry,
    frame_shape: Tuple[int, int]
) -> bool:
    """
    Simple sanity check for geometry parameters.
    """
    height, width = frame_shape[:2]
    
    # Center must be somewhat reasonable (within 50% margin of frame)
    margin_w = width * 0.5
    margin_h = height * 0.5
    
    if (geometry.drum_center_x_px < -margin_w or 
        geometry.drum_center_x_px > width + margin_w):
        return False
        
    if (geometry.drum_center_y_px < -margin_h or 
        geometry.drum_center_y_px > height + margin_h):
        return False
        
    if geometry.effective_radius_px <= 0:
        return False
        
    return True
