"""
Detection module for MillPresenter pipeline.

STEP_04: Candidate Generation (Circle Detection)

This module detects circular bead candidates using HoughCircles.
All detection operates in pixel-space only.

Output: Raw candidates (x, y, r_px) - no filtering, no confidence at this stage.
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path


@dataclass
class Detection:
    """A single circle detection in pixel space."""
    x: int          # Center x coordinate (pixels)
    y: int          # Center y coordinate (pixels)
    r_px: float     # Radius in pixels
    
    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "r_px": round(self.r_px, 2)}
    
    @classmethod
    def from_dict(cls, data: dict) -> "Detection":
        return cls(x=int(data["x"]), y=int(data["y"]), r_px=float(data["r_px"]))


@dataclass 
class DetectionResult:
    """Result of detection on a single frame."""
    candidates: List[Detection]
    frame_shape: Tuple[int, int]  # (height, width)
    params_used: Dict[str, Any]   # Detection parameters used
    
    def to_dict(self) -> dict:
        return {
            "count": len(self.candidates),
            "frame_shape": list(self.frame_shape),
            "params_used": self.params_used,
            "candidates": [c.to_dict() for c in self.candidates]
        }


def calculate_radius_range(
    drum_radius_px: int,
    config: Dict[str, Any]
) -> Tuple[int, int]:
    """
    Calculate expected bead radius range in pixels based on drum geometry.
    
    Args:
        drum_radius_px: Drum radius in pixels
        config: DETECTION_BEAD_CONFIG dict
        
    Returns:
        (min_radius, max_radius) in pixels
    """
    drum_diameter_mm = config.get("drum_diameter_mm", 200)
    min_bead_mm = config.get("min_bead_diameter_mm", 3.0)
    max_bead_mm = config.get("max_bead_diameter_mm", 12.0)
    margin_low = config.get("radius_margin_low", 0.7)
    margin_high = config.get("radius_margin_high", 1.5)
    
    # Calculate px_per_mm for this video
    px_per_mm = (drum_radius_px * 2) / drum_diameter_mm
    
    # Calculate expected radius range
    min_radius_expected = (min_bead_mm / 2) * px_per_mm
    max_radius_expected = (max_bead_mm / 2) * px_per_mm
    
    # Apply safety margins
    min_radius = max(3, int(min_radius_expected * margin_low))
    max_radius = int(max_radius_expected * margin_high)
    
    return min_radius, max_radius


def detect_candidates(
    frame: np.ndarray,
    drum_radius_px: int,
    config: Optional[Dict[str, Any]] = None
) -> DetectionResult:
    """
    Detect circle candidates in a preprocessed frame.
    
    Args:
        frame: Preprocessed grayscale frame
        drum_radius_px: Drum radius in pixels (for radius range calculation)
        config: Detection configuration dict. If None, uses defaults.
        
    Returns:
        DetectionResult with list of candidates
    """
    # Import here to avoid circular dependency
    from config import DETECTION_BEAD_CONFIG
    
    if config is None:
        config = DETECTION_BEAD_CONFIG.copy()
    
    # Ensure grayscale
    if len(frame.shape) == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame
    
    h, w = gray.shape[:2]
    
    # Calculate radius range
    min_radius, max_radius = calculate_radius_range(drum_radius_px, config)
    
    # Calculate minDist
    min_dist = max(1, int(min_radius * config.get("min_dist_ratio", 0.5)))
    
    # Extract HoughCircles parameters
    dp = config.get("dp", 1)
    param1 = config.get("param1", 50)
    
    # Resolution-adaptive param2
    # Base param2 is tuned for 1080p. Scale up for higher resolutions.
    base_param2 = config.get("param2", 25)
    resolution_factor = h / 1080.0
    if resolution_factor > 1.2:
        # For 4K (2160p), factor = 2.0
        # Increase param2 moderately to reduce noise without losing beads
        param2 = int(base_param2 + (resolution_factor - 1) * 10)
    else:
        param2 = base_param2
    
    # Store params for logging
    params_used = {
        "dp": dp,
        "minDist": min_dist,
        "param1": param1,
        "param2": param2,
        "minRadius": min_radius,
        "maxRadius": max_radius,
        "drum_radius_px": drum_radius_px,
    }
    
    # Run HoughCircles
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
    
    # Convert to Detection objects
    candidates = []
    if circles is not None:
        for circle in circles[0]:
            x, y, r = circle
            candidates.append(Detection(
                x=int(round(x)),
                y=int(round(y)),
                r_px=float(r)
            ))
    
    return DetectionResult(
        candidates=candidates,
        frame_shape=(h, w),
        params_used=params_used
    )


def create_detection_overlay(
    frame: np.ndarray,
    result: DetectionResult,
    color: Tuple[int, int, int] = (0, 255, 0),
    thickness: int = 2
) -> np.ndarray:
    """
    Create visualization overlay showing detected candidates.
    
    Args:
        frame: Original BGR frame (or grayscale, will be converted)
        result: DetectionResult from detect_candidates
        color: Circle color in BGR
        thickness: Line thickness
        
    Returns:
        BGR image with detection overlay
    """
    # Ensure BGR
    if len(frame.shape) == 2:
        overlay = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    else:
        overlay = frame.copy()
    
    # Draw each candidate
    for det in result.candidates:
        # Circle outline
        cv2.circle(overlay, (det.x, det.y), int(det.r_px), color, thickness)
        # Center dot
        cv2.circle(overlay, (det.x, det.y), 2, color, -1)
    
    # Add count label
    count_text = f"Candidates: {len(result.candidates)}"
    cv2.putText(overlay, count_text, (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
    
    # Add params info
    params = result.params_used
    params_text = f"r={params['minRadius']}-{params['maxRadius']}px, param2={params['param2']}"
    cv2.putText(overlay, params_text, (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    return overlay


def imread_unicode(path: Path) -> np.ndarray:
    """Read image with unicode path support."""
    with open(path, 'rb') as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def imwrite_unicode(path: Path, img: np.ndarray) -> bool:
    """Write image with unicode path support."""
    ext = path.suffix
    success, data = cv2.imencode(ext, img)
    if success:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data.tobytes())
        return True
    return False
