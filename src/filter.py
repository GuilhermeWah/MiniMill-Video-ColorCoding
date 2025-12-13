"""
Filtering module for MillPresenter pipeline.

STEP_06: Filtering and Cleanup

This module applies three sequential filters to reduce false positives:
1. Rim margin filter - Remove detections in outer rim zone
2. Confidence threshold - Remove low-confidence detections
3. Non-maximum suppression - Merge overlapping detections

All filters operate in pixel-space. Calibration (px_per_mm) is NOT used.
"""

import math
import numpy as np
import cv2
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path


@dataclass
class FilteredDetection:
    """A detection that passed all filters."""
    x: int
    y: int
    r_px: float
    conf: float
    
    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "r_px": round(self.r_px, 2),
            "conf": round(self.conf, 3)
        }


@dataclass
class FilterStats:
    """Statistics from filtering process."""
    input_count: int
    after_rim: int
    after_confidence: int
    after_nms: int
    rim_rejected: int
    confidence_rejected: int
    nms_suppressed: int
    
    def to_dict(self) -> dict:
        return {
            "input_count": self.input_count,
            "after_rim": self.after_rim,
            "after_confidence": self.after_confidence,
            "after_nms": self.after_nms,
            "rim_rejected": self.rim_rejected,
            "confidence_rejected": self.confidence_rejected,
            "nms_suppressed": self.nms_suppressed,
            "total_rejected": self.input_count - self.after_nms,
            "retention_rate": round(self.after_nms / self.input_count, 3) if self.input_count > 0 else 0
        }


def filter_rim_margin(
    detections: List[Dict],
    drum_center: Tuple[int, int],
    drum_radius: int,
    rim_margin_ratio: float = 0.12
) -> Tuple[List[Dict], int]:
    """
    Filter 1: Reject detections in the outer rim zone.
    
    Args:
        detections: List of detection dicts with x, y, r_px, conf
        drum_center: (center_x, center_y) of drum
        drum_radius: Radius of drum in pixels
        rim_margin_ratio: Fraction of radius to exclude (default 12%)
        
    Returns:
        (filtered_detections, count_rejected)
    """
    inner_radius = drum_radius * (1 - rim_margin_ratio)
    
    filtered = []
    rejected = 0
    
    for det in detections:
        x, y = det["x"], det["y"]
        dist = math.sqrt((x - drum_center[0])**2 + (y - drum_center[1])**2)
        
        if dist < inner_radius:
            filtered.append(det)
        else:
            rejected += 1
    
    return filtered, rejected


def filter_confidence(
    detections: List[Dict],
    min_confidence: float = 0.5
) -> Tuple[List[Dict], int]:
    """
    Filter 2: Reject detections below confidence threshold.
    
    Args:
        detections: List of detection dicts with conf field
        min_confidence: Minimum confidence to keep
        
    Returns:
        (filtered_detections, count_rejected)
    """
    filtered = []
    rejected = 0
    
    for det in detections:
        if det["conf"] >= min_confidence:
            filtered.append(det)
        else:
            rejected += 1
    
    return filtered, rejected


def filter_nms(
    detections: List[Dict],
    overlap_threshold: float = 0.5
) -> Tuple[List[Dict], int]:
    """
    Filter 3: Non-maximum suppression for overlapping detections.
    
    Two circles are considered overlapping if the distance between
    their centers is less than (r1 + r2) * overlap_threshold.
    
    Args:
        detections: List of detection dicts with x, y, r_px, conf
        overlap_threshold: Fraction of combined radii for overlap
        
    Returns:
        (filtered_detections, count_suppressed)
    """
    if not detections:
        return [], 0
    
    # Sort by confidence descending
    sorted_dets = sorted(detections, key=lambda d: d["conf"], reverse=True)
    
    kept = []
    suppressed = set()
    
    for i, det in enumerate(sorted_dets):
        if i in suppressed:
            continue
        
        kept.append(det)
        
        # Suppress overlapping lower-confidence detections
        for j in range(i + 1, len(sorted_dets)):
            if j in suppressed:
                continue
            
            other = sorted_dets[j]
            dist = math.sqrt((det["x"] - other["x"])**2 + (det["y"] - other["y"])**2)
            threshold = (det["r_px"] + other["r_px"]) * overlap_threshold
            
            if dist < threshold:
                suppressed.add(j)
    
    return kept, len(suppressed)


def apply_filters(
    detections: List[Dict],
    drum_center: Tuple[int, int],
    drum_radius: int,
    config: Optional[Dict[str, Any]] = None
) -> Tuple[List[FilteredDetection], FilterStats]:
    """
    Apply all three filters in sequence.
    
    Args:
        detections: Raw detections with x, y, r_px, conf
        drum_center: (center_x, center_y) of drum
        drum_radius: Drum radius in pixels
        config: Filter configuration (uses FILTER_CONFIG if None)
        
    Returns:
        (filtered_detections, filter_stats)
    """
    from config import FILTER_CONFIG
    
    if config is None:
        config = FILTER_CONFIG.copy()
    
    input_count = len(detections)
    
    # Filter 1: Rim margin
    rim_ratio = config.get("rim_margin_ratio", 0.12)
    after_rim, rim_rejected = filter_rim_margin(
        detections, drum_center, drum_radius, rim_ratio
    )
    
    # Filter 2: Confidence threshold
    min_conf = config.get("min_confidence", 0.5)
    after_conf, conf_rejected = filter_confidence(after_rim, min_conf)
    
    # Filter 3: NMS
    nms_threshold = config.get("nms_overlap_threshold", 0.5)
    after_nms, nms_suppressed = filter_nms(after_conf, nms_threshold)
    
    # Convert to FilteredDetection objects
    filtered = [
        FilteredDetection(
            x=d["x"],
            y=d["y"],
            r_px=d["r_px"],
            conf=d["conf"]
        )
        for d in after_nms
    ]
    
    # Collect stats
    stats = FilterStats(
        input_count=input_count,
        after_rim=len(after_rim),
        after_confidence=len(after_conf),
        after_nms=len(after_nms),
        rim_rejected=rim_rejected,
        confidence_rejected=conf_rejected,
        nms_suppressed=nms_suppressed
    )
    
    return filtered, stats


def create_filter_overlay(
    frame: np.ndarray,
    before: List[Dict],
    after: List[FilteredDetection],
    drum_center: Tuple[int, int],
    drum_radius: int,
    rim_margin_ratio: float = 0.12,
    thickness: int = 2
) -> np.ndarray:
    """
    Create before/after comparison overlay.
    
    Shows:
    - Inner ROI circle (white dashed)
    - Rejected detections (red, faded)
    - Kept detections (green, solid)
    """
    # Ensure BGR
    if len(frame.shape) == 2:
        base = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    else:
        base = frame.copy()
    
    # Create overlay for blending
    overlay = base.copy()
    
    # Draw inner ROI boundary (where rim margin starts)
    inner_radius = int(drum_radius * (1 - rim_margin_ratio))
    cv2.circle(overlay, drum_center, inner_radius, (255, 255, 255), 1, cv2.LINE_AA)
    
    # Draw outer drum boundary
    cv2.circle(overlay, drum_center, drum_radius, (100, 100, 100), 1, cv2.LINE_AA)
    
    # Create set of kept detection positions for comparison
    kept_set = set((d.x, d.y, round(d.r_px, 1)) for d in after)
    
    # Draw rejected detections (red, faded)
    for det in before:
        key = (det["x"], det["y"], round(det["r_px"], 1))
        if key not in kept_set:
            cv2.circle(overlay, (det["x"], det["y"]), int(det["r_px"]), 
                      (0, 0, 180), 1)
    
    # Draw kept detections (green, solid)
    for det in after:
        cv2.circle(overlay, (det.x, det.y), int(det.r_px), 
                  (0, 255, 0), thickness)
        cv2.circle(overlay, (det.x, det.y), 2, (0, 255, 0), -1)
    
    # Blend
    alpha = 0.85
    result = cv2.addWeighted(overlay, alpha, base, 1 - alpha, 0)
    
    # Add stats text
    h = result.shape[0]
    before_count = len(before)
    after_count = len(after)
    reduction = 100 * (1 - after_count / before_count) if before_count > 0 else 0
    
    cv2.putText(result, f"Before: {before_count}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.putText(result, f"After: {after_count}", (10, 55),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(result, f"Reduction: {reduction:.1f}%", (10, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    return result


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
