"""
Configuration module for MillPresenter pipeline.

STEP_01: Drum Geometry & ROI Stabilization
This module handles loading and saving geometry configuration.

All parameters are exposed via configuration files (JSON).
No hard-coded constants.

REFACTOR NOTE (2025-12-12, PM Approved):
- Changed from single global config to per-video auto-detection with caching
- Geometry is auto-detected via HoughCircles using frame-relative parameters
- Cached per video using filename hash to avoid re-detection
- Resolution-agnostic: works with 4K, 1080p, or any resolution
"""

import json
import os
import hashlib
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np


@dataclass
class DrumGeometry:
    """
    Drum geometry parameters in pixel space.
    
    Attributes:
        drum_center_x_px: Horizontal center of the drum (pixels).
        drum_center_y_px: Vertical center of the drum (pixels).
        drum_radius_px: Pixel radius of the grindable area.
        rim_margin_px: Buffer zone to exclude edge artifacts (bolts/liners).
        source: How geometry was obtained ('auto', 'cached', 'manual', 'default').
    """
    drum_center_x_px: int
    drum_center_y_px: int
    drum_radius_px: int
    rim_margin_px: int
    source: str = "default"
    
    @property
    def effective_radius_px(self) -> int:
        """Effective radius after applying rim margin."""
        return self.drum_radius_px - self.rim_margin_px
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "drum_center_x_px": self.drum_center_x_px,
            "drum_center_y_px": self.drum_center_y_px,
            "drum_radius_px": self.drum_radius_px,
            "rim_margin_px": self.rim_margin_px,
            "effective_radius_px": self.effective_radius_px,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "DrumGeometry":
        """Create DrumGeometry from dictionary."""
        return cls(
            drum_center_x_px=int(data["drum_center_x_px"]),
            drum_center_y_px=int(data["drum_center_y_px"]),
            drum_radius_px=int(data["drum_radius_px"]),
            rim_margin_px=int(data["rim_margin_px"]),
            source=data.get("source", "cached")
        )


# =============================================================================
# Directory Structure
# =============================================================================

# Production configs (version-controlled)
CONFIG_DIR = "config"

# Auto-generated cache (gitignored)
CACHE_DIR = "cache"
GEOMETRY_CACHE_DIR = os.path.join(CACHE_DIR, "geometry")

# Debug/test outputs (gitignored)
OUTPUT_DIR = "output"
DEBUG_DIR = os.path.join(OUTPUT_DIR, "debug")


# =============================================================================
# Auto-Detection Parameters (Frame-Relative, No Hard-Coding)
# =============================================================================

# Detection parameters based on proven ROI mask system approach
# Key insight: Scale relative to HEIGHT (not min dimension) for consistent results
DETECTION_CONFIG = {
    # HoughCircles parameters (relative to frame HEIGHT)
    "min_radius_ratio": 0.35,    # 35% of height - captures smaller/further drums
    "max_radius_ratio": 0.48,    # 48% of height - captures larger/closer drums
    "min_dist_ratio": 0.50,      # Min distance between circles (relative to height)
    
    # HoughCircles tuning (proven values from ROI mask system)
    "dp": 1,                     # Inverse ratio of accumulator resolution
    "param1": 50,                # High Canny threshold - strict edge detection
    "param2": 30,                # Accumulator threshold - balances sensitivity
    
    # Preprocessing
    "blur_kernel": 7,            # Median blur kernel - suppresses bolts/rocks
    
    # Rim margin as fraction of detected radius
    "rim_margin_ratio": 0.04,    # 4% of radius excluded as rim margin
    
    # Radius adjustment (stay inside visible rim)
    "radius_adjustment": 0.96,   # Use 96% of detected radius
}


# =============================================================================
# Preprocessing Configuration (STEP_03)
# =============================================================================

PREPROCESS_CONFIG = {
    # Stage toggles - each stage can be independently enabled/disabled
    "enable_tophat": True,           # Stage 3: Illumination normalization
    "enable_clahe": True,            # Stage 4: Contrast enhancement
    "enable_blur": True,             # Stage 5: Noise reduction
    "enable_glare_suppression": False,  # Stage 6: Glare handling (start disabled)
    
    # Stage 3: Top-hat Transform
    # Extracts bright features (beads) relative to local background
    "tophat_kernel_size": 21,        # Odd number, ~21-31px works well
    
    # Stage 4: CLAHE (Contrast Limited Adaptive Histogram Equalization)
    # Enhances local contrast without amplifying noise globally
    "clahe_clip_limit": 3.0,         # 2.0-4.0 typical range
    "clahe_tile_grid_size": (8, 8),  # Grid size for local histograms
    
    # Stage 5: Noise Reduction
    # Bilateral filter preserves edges while smoothing flat regions
    "blur_type": "bilateral",        # "bilateral" | "gaussian" | "median"
    "blur_diameter": 7,              # Filter diameter (odd number)
    "blur_sigma_color": 75,          # Color space sigma (bilateral only)
    "blur_sigma_space": 75,          # Coordinate space sigma (bilateral only)
    
    # Stage 6: Glare Suppression (when enabled)
    # Handles specular reflections on metallic beads
    "glare_threshold": 245,          # Intensity above this is considered glare
    "glare_mode": "cap",             # "cap" | "inpaint" | "none"
}


# =============================================================================
# Bead Detection Configuration (STEP_04)
# =============================================================================

DETECTION_BEAD_CONFIG = {
    # Bead size assumptions (for radius range calculation)
    # Physical drum diameter - used to calculate px_per_mm per video
    "drum_diameter_mm": 200,
    
    # Expected bead diameters (with margins for detection)
    "min_bead_diameter_mm": 3.0,     # Allow smaller than 4mm nominal
    "max_bead_diameter_mm": 12.0,    # Allow larger than 10mm nominal
    
    # HoughCircles parameters
    "dp": 1,                         # Accumulator resolution (1 = same as input)
    "min_dist_ratio": 0.5,           # minDist as ratio of min_radius
    "param1": 50,                    # Canny high threshold
    "param2": 25,                    # Accumulator threshold (lower = more candidates)
    
    # Safety margins for radius range
    "radius_margin_low": 0.7,        # Allow 30% smaller than calculated min
    "radius_margin_high": 1.5,       # Allow 50% larger than calculated max
}


# =============================================================================
# Confidence Scoring Configuration (STEP_05)
# =============================================================================

CONFIDENCE_CONFIG = {
    # Feature weights (should sum to 1.0)
    "weight_edge_strength": 0.35,    # Gradient magnitude along circumference
    "weight_circularity": 0.25,      # Edge consistency around perimeter
    "weight_interior": 0.20,         # Bead-like intensity pattern inside
    "weight_radius_fit": 0.20,       # Match to expected bead sizes
    
    # Edge sampling parameters
    "edge_sample_points": 36,        # Points around circumference
    "edge_gradient_sigma": 1.0,      # Gaussian sigma for gradient
    
    # Interior analysis
    "interior_sample_ratio": 0.7,    # Sample within 70% of radius
    
    # Radius fit scoring
    "radius_fit_optimal_min": 0.2,   # Optimal starts at 20% into range
    "radius_fit_optimal_max": 0.8,   # Optimal ends at 80% of range
}


# =============================================================================
# Filtering Configuration (STEP_06)
# =============================================================================

FILTER_CONFIG = {
    # Rim margin filter (applied first)
    # Rejects detections in outer rim zone (bolts, purple ring, edge artifacts)
    "rim_margin_ratio": 0.12,        # 12% of drum radius excluded
    
    # Confidence threshold (applied second)
    # Rejects low-confidence noise detections
    "min_confidence": 0.5,           # Minimum confidence to keep
    
    # Non-maximum suppression (applied last)
    # Merges overlapping detections, keeps highest confidence
    "nms_overlap_threshold": 0.5,    # 50% overlap triggers suppression
    
    # Filter order (do not change unless necessary)
    "filter_order": ["rim", "confidence", "nms"],
}


# =============================================================================
# Size Classification Configuration (STEP_07)
# =============================================================================

SIZE_CONFIG = {
    # Physical drum diameter (known constant)
    "drum_diameter_mm": 200.0,
    
    # Size bins: class name -> (min_mm, max_mm)
    # Based on actual bead sizes: 3.94mm, 5.79mm, 7.63mm, 9.90mm
    # Bins widened to reduce "unknown" edge cases
    "size_bins": {
        "4mm": (2.0, 5.0),      # 3.94mm nominal, catch 2.0-5.0mm
        "6mm": (5.0, 7.0),      # 5.79mm nominal, catch 5.0-7.0mm
        "8mm": (7.0, 9.0),      # 7.63mm nominal, catch 7.0-9.0mm
        "10mm": (9.0, 13.0),    # 9.90mm nominal, catch 9.0-13.0mm
    },
    
    # Color scheme for visualization (BGR format)
    # UI Spec v2.0: 4mm=Blue, 6mm=Green, 8mm=Orange, 10mm=Red
    "class_colors": {
        "4mm": (255, 0, 0),        # Blue (#0000FF)
        "6mm": (0, 255, 0),        # Green (#00FF00)
        "8mm": (0, 165, 255),      # Orange (#FFA500)
        "10mm": (0, 0, 255),       # Red (#FF0000)
        "unknown": (128, 128, 128) # Gray
    },
    
    # Label display options
    # Labels disabled by default - UI shows on hover/selection
    "show_size_label": False,
    "show_diameter_mm": False,
    "label_font_scale": 0.5,
    
    # Visual options
    "circle_thickness": 2,        # 2px (OpenCV requires integer; 40% opacity makes it appear thinner)
    "center_dot_radius": 2,       # Center dot size
    "overlay_opacity": 0.4,       # 40% opacity for overlay (0.0-1.0)
    "use_antialiasing": True,     # Smoother circle edges
}


def get_video_hash(video_path: str) -> str:
    """Generate a short hash from video filename for cache key."""
    filename = os.path.basename(video_path)
    return hashlib.md5(filename.encode()).hexdigest()[:8]


def get_video_cache_name(video_path: str) -> str:
    """Generate a readable cache filename: {video_name}_{hash}.json"""
    filename = os.path.basename(video_path)
    name_part = os.path.splitext(filename)[0]  # Remove extension
    hash_part = get_video_hash(video_path)
    return f"{name_part}_{hash_part}.json"


def get_geometry_cache_path(video_path: str, cache_dir: str = None) -> str:
    """Get the cache file path for a specific video's geometry."""
    if cache_dir is None:
        cache_dir = GEOMETRY_CACHE_DIR
    cache_name = get_video_cache_name(video_path)
    return os.path.join(cache_dir, cache_name)


def get_manual_override_path(config_dir: str = None) -> str:
    """Get the path for manual geometry overrides file."""
    if config_dir is None:
        config_dir = CONFIG_DIR
    return os.path.join(config_dir, "geometry_overrides.json")


def load_manual_overrides(config_dir: str = None) -> dict:
    """
    Load manual geometry overrides.
    
    The overrides file maps video filenames to geometry parameters.
    Users can edit this file to manually correct auto-detection errors.
    
    Example geometry_overrides.json:
    {
        "IMG_6535.MOV": {
            "drum_center_x_px": 1820,
            "drum_center_y_px": 1080,
            "drum_radius_px": 870,
            "rim_margin_px": 35
        },
        "problematic_video.mp4": {
            "drum_center_x_px": 960,
            "drum_center_y_px": 540,
            "drum_radius_px": 400,
            "rim_margin_px": 16
        }
    }
    """
    if config_dir is None:
        config_dir = CONFIG_DIR
    override_path = get_manual_override_path(config_dir)
    if os.path.exists(override_path):
        with open(override_path, 'r') as f:
            return json.load(f)
    return {}


def save_manual_override(
    video_path: str, 
    geometry: 'DrumGeometry', 
    config_dir: str = None
) -> str:
    """
    Save a manual geometry override for a specific video.
    
    Returns the path to the overrides file.
    """
    if config_dir is None:
        config_dir = CONFIG_DIR
    override_path = get_manual_override_path(config_dir)
    overrides = load_manual_overrides(config_dir)
    
    video_name = os.path.basename(video_path)
    overrides[video_name] = {
        "drum_center_x_px": geometry.drum_center_x_px,
        "drum_center_y_px": geometry.drum_center_y_px,
        "drum_radius_px": geometry.drum_radius_px,
        "rim_margin_px": geometry.rim_margin_px
    }
    
    os.makedirs(config_dir, exist_ok=True)
    with open(override_path, 'w') as f:
        json.dump(overrides, f, indent=2)
    
    return override_path


def auto_detect_drum(
    frame: np.ndarray,
    config: dict = None
) -> Optional[DrumGeometry]:
    """
    Auto-detect drum geometry from a video frame using HoughCircles.
    
    Uses HEIGHT-relative parameters (proven approach from roi_mask_system).
    The drum circle is typically 35-48% of the frame height.
    
    Args:
        frame: BGR image (first frame of video typically)
        config: Detection parameters (uses DETECTION_CONFIG if None)
        
    Returns:
        DrumGeometry if detection successful, None otherwise
    """
    if config is None:
        config = DETECTION_CONFIG
    
    height, width = frame.shape[:2]
    
    # Use HEIGHT for radius calculations (proven approach)
    # The drum circle radius is typically 35-48% of frame height
    min_radius = int(height * config["min_radius_ratio"])
    max_radius = int(height * config["max_radius_ratio"])
    min_dist = int(height * config["min_dist_ratio"])
    
    # Convert to grayscale and apply median blur
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur_kernel = config.get("blur_kernel", 7)
    gray = cv2.medianBlur(gray, blur_kernel)
    
    # Detect circles
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=config["dp"],
        minDist=min_dist,
        param1=config["param1"],
        param2=config["param2"],
        minRadius=min_radius,
        maxRadius=max_radius
    )
    
    if circles is None:
        return None
    
    # HoughCircles returns circles sorted by accumulator votes (strongest first)
    # The proven approach: take the FIRST (strongest) circle
    # This is more reliable than weighted scoring for drums
    x, y, r = circles[0][0]
    
    # Apply radius adjustment (stay inside visible rim)
    adjusted_radius = int(r * config["radius_adjustment"])
    
    # Calculate rim margin
    rim_margin = int(adjusted_radius * config["rim_margin_ratio"])
    
    return DrumGeometry(
        drum_center_x_px=int(x),
        drum_center_y_px=int(y),
        drum_radius_px=adjusted_radius,
        rim_margin_px=rim_margin,
        source="auto"
    )


def load_geometry_for_video(
    video_path: str,
    frame: np.ndarray = None,
    config_dir: str = None,
    cache_dir: str = None,
    force_detect: bool = False
) -> Tuple[DrumGeometry, str]:
    """
    Load or auto-detect geometry for a specific video.
    
    Priority (highest to lowest):
    1. Manual override (config/geometry_overrides.json) — always wins
    2. Cached geometry (cache/geometry/{name}_{hash}.json) — unless force_detect
    3. Auto-detection via HoughCircles — if frame provided
    4. Frame-based default (centered, 40% radius)
    5. Absolute fallback default
    
    Args:
        video_path: Path to video file
        frame: First frame of video (for auto-detection)
        config_dir: Directory for manual overrides (default: config/)
        cache_dir: Directory for geometry cache (default: cache/geometry/)
        force_detect: If True, skip cache and re-detect (but NOT manual overrides)
        
    Returns:
        Tuple of (DrumGeometry, status_message)
    """
    if config_dir is None:
        config_dir = CONFIG_DIR
    if cache_dir is None:
        cache_dir = GEOMETRY_CACHE_DIR
    
    video_name = os.path.basename(video_path)
    cache_path = get_geometry_cache_path(video_path, cache_dir)
    
    # 1. Check manual overrides FIRST (always wins, even with force_detect)
    overrides = load_manual_overrides(config_dir)
    if video_name in overrides:
        data = overrides[video_name]
        geometry = DrumGeometry(
            drum_center_x_px=int(data["drum_center_x_px"]),
            drum_center_y_px=int(data["drum_center_y_px"]),
            drum_radius_px=int(data["drum_radius_px"]),
            rim_margin_px=int(data["rim_margin_px"]),
            source="manual"
        )
        return geometry, f"Loaded MANUAL override for '{video_name}'"
    
    # 2. Try cached geometry (unless force_detect)
    if not force_detect and os.path.exists(cache_path):
        geometry = load_geometry(cache_path)
        geometry.source = "cached"
        return geometry, f"Loaded cached geometry: {os.path.basename(cache_path)}"
    
    # 3. Try auto-detection if frame provided
    if frame is not None:
        geometry = auto_detect_drum(frame)
        if geometry is not None:
            # Cache the result
            os.makedirs(cache_dir, exist_ok=True)
            save_geometry(geometry, cache_path)
            return geometry, f"Auto-detected and cached: {os.path.basename(cache_path)}"
    
    # 4. Fall back to default (frame-center based)
    if frame is not None:
        h, w = frame.shape[:2]
        min_dim = min(w, h)
        default_radius = int(min_dim * 0.40)
        default_margin = int(default_radius * 0.04)
        geometry = DrumGeometry(
            drum_center_x_px=w // 2,
            drum_center_y_px=h // 2,
            drum_radius_px=default_radius,
            rim_margin_px=default_margin,
            source="default"
        )
    else:
        geometry = get_default_geometry()
    
    return geometry, "Using default geometry (auto-detection failed)"


def get_default_geometry() -> DrumGeometry:
    """
    Return fallback default geometry.
    
    NOTE: This is only used when no frame is available for auto-detection
    and no cached geometry exists. Values assume 1080p as baseline.
    """
    return DrumGeometry(
        drum_center_x_px=960,
        drum_center_y_px=540,
        drum_radius_px=400,
        rim_margin_px=16,
        source="default"
    )


def load_geometry(config_path: str) -> DrumGeometry:
    """Load drum geometry from JSON config or return defaults."""
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            data = json.load(f)
        return DrumGeometry.from_dict(data)
    else:
        return get_default_geometry()


def save_geometry(geometry: DrumGeometry, config_path: str) -> None:
    """Save drum geometry to JSON config."""
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(geometry.to_dict(), f, indent=2)
