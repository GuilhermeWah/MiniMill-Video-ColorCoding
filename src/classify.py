"""
Size classification module for MillPresenter pipeline.

STEP_07: Size Classification

This module converts pixel radii to physical sizes and classifies beads
into size categories (4mm, 6mm, 8mm, 10mm).

CRITICAL: Classification happens POST-DETECTION.
- Changing px_per_mm reclassifies sizes but does NOT change detections
- Detection (x, y, r_px) remains in pixel-space
- Only the 'cls' label changes based on calibration

Target bead sizes (nominal diameters):
- 4mm: 3.94mm actual
- 6mm: 5.79mm actual
- 8mm: 7.63mm actual
- 10mm: 9.90mm actual
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class ClassifiedDetection:
    """A detection with size classification."""
    x: int
    y: int
    r_px: float
    conf: float
    diameter_mm: float
    cls: str
    
    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "r_px": round(self.r_px, 2),
            "conf": round(self.conf, 3),
            "diameter_mm": round(self.diameter_mm, 2),
            "cls": self.cls
        }


@dataclass 
class ClassificationStats:
    """Statistics from classification process."""
    total_count: int
    count_4mm: int
    count_6mm: int
    count_8mm: int
    count_10mm: int
    count_unknown: int
    px_per_mm_used: float
    
    def to_dict(self) -> dict:
        return {
            "total_count": self.total_count,
            "by_class": {
                "4mm": self.count_4mm,
                "6mm": self.count_6mm,
                "8mm": self.count_8mm,
                "10mm": self.count_10mm,
                "unknown": self.count_unknown
            },
            "percentages": {
                "4mm": round(100 * self.count_4mm / self.total_count, 1) if self.total_count > 0 else 0,
                "6mm": round(100 * self.count_6mm / self.total_count, 1) if self.total_count > 0 else 0,
                "8mm": round(100 * self.count_8mm / self.total_count, 1) if self.total_count > 0 else 0,
                "10mm": round(100 * self.count_10mm / self.total_count, 1) if self.total_count > 0 else 0,
                "unknown": round(100 * self.count_unknown / self.total_count, 1) if self.total_count > 0 else 0
            },
            "px_per_mm_used": round(self.px_per_mm_used, 3)
        }


def calculate_px_per_mm(drum_radius_px: int, drum_diameter_mm: float = 200.0) -> float:
    """
    Calculate pixels per millimeter from drum geometry.
    
    Args:
        drum_radius_px: Detected drum radius in pixels
        drum_diameter_mm: Known physical drum diameter (default 200mm)
        
    Returns:
        px_per_mm: Conversion factor from pixels to millimeters
    """
    drum_radius_mm = drum_diameter_mm / 2.0
    return drum_radius_px / drum_radius_mm


def classify_diameter(diameter_mm: float, size_bins: Dict[str, Tuple[float, float]]) -> str:
    """
    Classify a diameter into a size bin.
    
    Args:
        diameter_mm: Measured diameter in millimeters
        size_bins: Dict mapping class name to (min_mm, max_mm) range
        
    Returns:
        Class name ("4mm", "6mm", "8mm", "10mm") or "unknown"
    """
    for cls_name, (min_mm, max_mm) in size_bins.items():
        if min_mm <= diameter_mm < max_mm:
            return cls_name
    return "unknown"


def classify_detection(
    detection: Dict[str, Any],
    px_per_mm: float,
    size_bins: Dict[str, Tuple[float, float]]
) -> ClassifiedDetection:
    """
    Add size classification to a single detection.
    
    Args:
        detection: Dict with x, y, r_px, conf
        px_per_mm: Pixels per millimeter conversion factor
        size_bins: Dict mapping class name to (min_mm, max_mm) range
        
    Returns:
        ClassifiedDetection with diameter_mm and cls added
    """
    r_px = detection["r_px"]
    diameter_px = 2 * r_px
    diameter_mm = diameter_px / px_per_mm
    
    cls = classify_diameter(diameter_mm, size_bins)
    
    return ClassifiedDetection(
        x=detection["x"],
        y=detection["y"],
        r_px=r_px,
        conf=detection["conf"],
        diameter_mm=diameter_mm,
        cls=cls
    )


def classify_detections(
    detections: List[Dict[str, Any]],
    px_per_mm: float,
    size_config: Dict[str, Any]
) -> Tuple[List[ClassifiedDetection], ClassificationStats]:
    """
    Classify all detections by size.
    
    Args:
        detections: List of detection dicts with x, y, r_px, conf
        px_per_mm: Pixels per millimeter conversion factor
        size_config: Configuration dict with size_bins
        
    Returns:
        (classified_detections, stats)
    """
    size_bins = size_config.get("size_bins", {
        "4mm": (2.5, 5.0),
        "6mm": (5.0, 7.0),
        "8mm": (7.0, 9.0),
        "10mm": (9.0, 12.0)
    })
    
    classified = []
    counts = {"4mm": 0, "6mm": 0, "8mm": 0, "10mm": 0, "unknown": 0}
    
    for det in detections:
        cls_det = classify_detection(det, px_per_mm, size_bins)
        classified.append(cls_det)
        counts[cls_det.cls] = counts.get(cls_det.cls, 0) + 1
    
    stats = ClassificationStats(
        total_count=len(detections),
        count_4mm=counts["4mm"],
        count_6mm=counts["6mm"],
        count_8mm=counts["8mm"],
        count_10mm=counts["10mm"],
        count_unknown=counts["unknown"],
        px_per_mm_used=px_per_mm
    )
    
    return classified, stats


def get_class_color(cls: str, color_scheme: Dict[str, Tuple[int, int, int]] = None) -> Tuple[int, int, int]:
    """
    Get BGR color for a size class.
    
    Args:
        cls: Size class name
        color_scheme: Optional custom color mapping
        
    Returns:
        BGR color tuple
    """
    if color_scheme is None:
        # Default colors (BGR format for OpenCV)
        color_scheme = {
            "4mm": (255, 100, 100),    # Light blue
            "6mm": (100, 255, 100),    # Light green
            "8mm": (100, 100, 255),    # Light red/salmon
            "10mm": (255, 255, 100),   # Cyan
            "unknown": (128, 128, 128) # Gray
        }
    
    return color_scheme.get(cls, (128, 128, 128))


def reclassify_with_new_calibration(
    classified_detections: List[ClassifiedDetection],
    new_px_per_mm: float,
    size_config: Dict[str, Any]
) -> Tuple[List[ClassifiedDetection], ClassificationStats]:
    """
    Reclassify existing detections with new calibration.
    
    This demonstrates calibration decoupling:
    - Same (x, y, r_px) coordinates
    - Different diameter_mm and cls based on new px_per_mm
    
    Args:
        classified_detections: Previously classified detections
        new_px_per_mm: New calibration value
        size_config: Configuration dict with size_bins
        
    Returns:
        (reclassified_detections, new_stats)
    """
    # Convert back to raw detection format
    raw_detections = [
        {"x": d.x, "y": d.y, "r_px": d.r_px, "conf": d.conf}
        for d in classified_detections
    ]
    
    # Reclassify with new calibration
    return classify_detections(raw_detections, new_px_per_mm, size_config)
