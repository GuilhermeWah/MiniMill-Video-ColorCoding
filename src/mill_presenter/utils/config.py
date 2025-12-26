# MillPresenter V2 - Utils Configuration

"""
Centralized configuration for the MillPresenter pipeline.
All parameters are exposed here for easy tuning and documentation.
"""

from typing import Dict, List, Any, Tuple, Optional

CONFIG: Dict[str, Any] = {
    # ===========================================================================
    # Drum Detection (STEP-02)
    # ===========================================================================
    "drum_min_radius_ratio": 0.35,  # Min drum radius as ratio of frame height
    "drum_max_radius_ratio": 0.48,  # Max drum radius as ratio of frame height
    "drum_diameter_mm": 160.0,      # Physical drum diameter (for calibration) - decreased to fix overestimation
    "drum_hough_dp": 1,
    "drum_hough_param1": 50,
    "drum_hough_param2": 30,
    "drum_blur_ksize": 5,
    
    # ===========================================================================
    # Preprocessing (STEP-03)
    # ===========================================================================
    "tophat_kernel_size": 15,       # Morphological top-hat kernel
    "clahe_clip_limit": 2.0,        # CLAHE contrast limit
    "clahe_tile_size": 8,           # CLAHE tile grid size
    "bilateral_d": 9,               # Bilateral filter diameter
    "bilateral_sigma_color": 75,    # Bilateral color sigma
    "bilateral_sigma_space": 75,    # Bilateral space sigma
    "glare_threshold": 250,         # Glare suppression threshold
    "glare_replacement": 200,       # Value to replace glare pixels
    
    # ===========================================================================
    # Detection (STEP-04)
    # ===========================================================================
    "hough_dp": 1,
    "hough_param1": 50,             # Canny high threshold
    "hough_param2_base": 25,        # Accumulator base threshold (scaled by resolution)
    "hough_min_dist_ratio": 0.5,    # minDist as ratio of min_radius
    "contour_min_circularity": 0.65,# Circularity threshold for contour path
    "min_bead_diameter_mm": 3.0,    # Smallest expected bead
    "max_bead_diameter_mm": 12.0,   # Largest expected bead
    "radius_margin_low": 0.7,       # Shrink factor for min radius
    "radius_margin_high": 1.5,      # Expand factor for max radius
    
    # ===========================================================================
    # Confidence Scoring (STEP-05)
    # ===========================================================================
    "weight_edge_strength": 0.35,
    "weight_circularity": 0.25,
    "weight_interior": 0.20,
    "weight_radius_fit": 0.20,
    "edge_sample_points": 36,       # Points to sample around perimeter
    "edge_gradient_sigma": 1.0,     # Gaussian sigma for gradient computation
    "interior_sample_ratio": 0.7,   # Ratio of radius to sample interior
    
    # ===========================================================================
    # Filtering (STEP-06)
    # ===========================================================================
    "rim_margin_ratio": 0.12,       # Outer rim zone to exclude (12%)
    "brightness_threshold": 50,     # Min brightness (reject dark holes)
    "brightness_patch_size": 5,     # Patch size for brightness sampling
    "nms_overlap_threshold": 0.5,   # NMS overlap threshold
    "min_confidence": 0.50,         # Min confidence to keep
    
    # ===========================================================================
    # Classification (STEP-07)
    # ===========================================================================
    "bins_mm": [
        {"label": 4, "min": 3.0, "max": 5.0},
        {"label": 6, "min": 5.0, "max": 7.0},
        {"label": 8, "min": 7.0, "max": 9.0},
        {"label": 10, "min": 9.0, "max": 12.0},
    ],
    
    # ===========================================================================
    # Overlay Rendering
    # ===========================================================================
    "overlay_colors": {
        4: "#00BFFF",   # Deep Sky Blue
        6: "#00FF00",   # Green
        8: "#FF6B6B",   # Coral Red
        10: "#FFD700",  # Gold
        0: "#808080",   # Gray (unknown)
    },
    "overlay_line_width": 2,
    "overlay_default_opacity": 0.8,
    
    # ===========================================================================
    # Calibration (Manual Override)
    # ===========================================================================
    "calibration_px_per_mm": None,     # User-set px_per_mm (overrides auto)
    "calibration_source": "auto",       # "auto" or "manual"
    
    # ===========================================================================
    # ROI Mask (Detection Region)
    # ===========================================================================
    "roi_center_x": None,              # User-set ROI center X (overrides auto)
    "roi_center_y": None,              # User-set ROI center Y (overrides auto)
    "roi_radius": None,                # User-set ROI radius (overrides auto)
    "roi_source": "auto",              # "auto" or "manual"
}


def get_config() -> Dict[str, Any]:
    """Return a copy of the configuration dictionary."""
    return CONFIG.copy()


def get(key: str, default: Any = None) -> Any:
    """Get a configuration value by key."""
    return CONFIG.get(key, default)


# Calibration file path (next to config.py)
import json
from pathlib import Path
from datetime import datetime

_CALIBRATION_FILE = Path(__file__).parent.parent / "calibration.json"


def _load_calibration_from_file() -> None:
    """Load calibration from file on startup."""
    if _CALIBRATION_FILE.exists():
        try:
            with open(_CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
            if data.get("px_per_mm") is not None:
                CONFIG["calibration_px_per_mm"] = data["px_per_mm"]
                CONFIG["calibration_source"] = data.get("source", "manual")
                print(f"[CONFIG] Loaded calibration from file: {data['px_per_mm']:.4f} px/mm")
        except Exception as e:
            print(f"[CONFIG] Failed to load calibration: {e}")


def _save_calibration_to_file() -> None:
    """Save current calibration to file."""
    try:
        data = {
            "px_per_mm": CONFIG.get("calibration_px_per_mm"),
            "source": CONFIG.get("calibration_source", "auto"),
            "last_updated": datetime.now().isoformat()
        }
        with open(_CALIBRATION_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"[CONFIG] Calibration saved to {_CALIBRATION_FILE.name}")
    except Exception as e:
        print(f"[CONFIG] Failed to save calibration: {e}")


def set_calibration(px_per_mm: float) -> None:
    """
    Set manual calibration override and save to file.
    
    Args:
        px_per_mm: Calibration value from point-to-point measurement.
    """
    CONFIG["calibration_px_per_mm"] = px_per_mm
    CONFIG["calibration_source"] = "manual"
    _save_calibration_to_file()
    print(f"[CONFIG] Manual calibration set: px_per_mm = {px_per_mm:.4f}")


def clear_calibration() -> None:
    """Clear manual calibration and revert to auto mode."""
    CONFIG["calibration_px_per_mm"] = None
    CONFIG["calibration_source"] = "auto"
    _save_calibration_to_file()
    print("[CONFIG] Manual calibration cleared. Using auto mode.")


def get_calibration() -> Tuple[Optional[float], str]:
    """
    Get current calibration settings.
    
    Returns:
        Tuple of (px_per_mm or None, source: "auto" or "manual")
    """
    return CONFIG.get("calibration_px_per_mm"), CONFIG.get("calibration_source", "auto")


# ===========================================================================
# ROI Mask Functions
# ===========================================================================

_ROI_FILE = Path(__file__).parent.parent / "roi_mask.json"


def set_roi(center_x: int, center_y: int, radius: int) -> None:
    """
    Set manual ROI mask and save to file.
    
    Args:
        center_x: Center X coordinate of detection region
        center_y: Center Y coordinate of detection region  
        radius: Radius of detection region
    """
    CONFIG["roi_center_x"] = center_x
    CONFIG["roi_center_y"] = center_y
    CONFIG["roi_radius"] = radius
    CONFIG["roi_source"] = "manual"
    
    try:
        data = {
            "center_x": center_x,
            "center_y": center_y,
            "radius": radius,
            "source": "manual",
            "last_updated": datetime.now().isoformat()
        }
        with open(_ROI_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"[CONFIG] ROI saved: center=({center_x}, {center_y}), radius={radius}")
    except Exception as e:
        print(f"[CONFIG] Failed to save ROI: {e}")


def clear_roi() -> None:
    """Clear manual ROI and revert to auto mode."""
    CONFIG["roi_center_x"] = None
    CONFIG["roi_center_y"] = None
    CONFIG["roi_radius"] = None
    CONFIG["roi_source"] = "auto"
    
    try:
        if _ROI_FILE.exists():
            _ROI_FILE.unlink()
        print("[CONFIG] Manual ROI cleared. Using auto mode.")
    except Exception as e:
        print(f"[CONFIG] Failed to clear ROI file: {e}")


def get_roi() -> Tuple[Optional[int], Optional[int], Optional[int], str]:
    """
    Get current ROI mask settings.
    
    Returns:
        Tuple of (center_x, center_y, radius, source)
    """
    return (
        CONFIG.get("roi_center_x"),
        CONFIG.get("roi_center_y"),
        CONFIG.get("roi_radius"),
        CONFIG.get("roi_source", "auto")
    )


def _load_roi_from_file() -> None:
    """Load ROI from file on startup."""
    if _ROI_FILE.exists():
        try:
            with open(_ROI_FILE, 'r') as f:
                data = json.load(f)
            if data.get("center_x") is not None:
                CONFIG["roi_center_x"] = data["center_x"]
                CONFIG["roi_center_y"] = data["center_y"]
                CONFIG["roi_radius"] = data["radius"]
                CONFIG["roi_source"] = data.get("source", "manual")
                print(f"[CONFIG] Loaded ROI from file: center=({data['center_x']}, {data['center_y']}), radius={data['radius']}")
        except Exception as e:
            print(f"[CONFIG] Failed to load ROI: {e}")


# Load calibration and ROI on module import
_load_calibration_from_file()
_load_roi_from_file()

