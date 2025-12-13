"""
Preprocessing module for MillPresenter pipeline.

STEP_03: Preprocessing Baseline Stabilization

This module provides a deterministic preprocessing pipeline to improve bead visibility
before candidate generation. All operations are in pixel-space only.

Pipeline Stages:
1. Grayscale Conversion
2. ROI Application
3. Illumination Normalization (top-hat transform)
4. Contrast Enhancement (CLAHE)
5. Noise Reduction (bilateral/gaussian/median)
6. Glare Suppression (optional)

All parameters are configurable via PREPROCESS_CONFIG in config.py.
Each stage can be independently enabled/disabled.
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from pathlib import Path


@dataclass
class PreprocessResult:
    """Result of preprocessing a single frame."""
    original: np.ndarray          # Original BGR frame
    gray: np.ndarray              # Grayscale version
    preprocessed: np.ndarray      # Final preprocessed grayscale
    stages: Dict[str, np.ndarray] # Intermediate stage outputs
    metrics: Dict[str, float]     # Quality metrics
    

def preprocess_frame(
    frame: np.ndarray,
    roi_mask: Optional[np.ndarray] = None,
    config: Optional[Dict[str, Any]] = None
) -> PreprocessResult:
    """
    Apply preprocessing pipeline to a single frame.
    
    Args:
        frame: Input BGR image
        roi_mask: Optional binary mask (255 = valid region, 0 = ignore)
        config: Preprocessing configuration dict. If None, uses defaults.
        
    Returns:
        PreprocessResult with original, preprocessed, stages, and metrics
    """
    # Import here to avoid circular dependency
    from config import PREPROCESS_CONFIG
    
    if config is None:
        config = PREPROCESS_CONFIG.copy()
    
    stages = {}
    
    # Store original
    original = frame.copy()
    stages["0_original"] = original
    
    # ==========================================================================
    # Stage 1: Grayscale Conversion
    # ==========================================================================
    if len(frame.shape) == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame.copy()
    stages["1_grayscale"] = gray.copy()
    
    # ==========================================================================
    # Stage 2: ROI Application
    # ==========================================================================
    if roi_mask is not None:
        # Ensure mask is single channel
        if len(roi_mask.shape) == 3:
            roi_mask = cv2.cvtColor(roi_mask, cv2.COLOR_BGR2GRAY)
        # Ensure mask is binary
        _, roi_mask = cv2.threshold(roi_mask, 127, 255, cv2.THRESH_BINARY)
        
        # Apply mask - set outside region to 0
        gray = cv2.bitwise_and(gray, gray, mask=roi_mask)
        stages["2_roi_applied"] = gray.copy()
    else:
        stages["2_roi_applied"] = gray.copy()
    
    # Track current working image
    current = gray.copy()
    
    # ==========================================================================
    # Stage 3: Illumination Normalization (Top-hat Transform)
    # ==========================================================================
    if config.get("enable_tophat", True):
        kernel_size = config.get("tophat_kernel_size", 21)
        # Ensure odd kernel size
        if kernel_size % 2 == 0:
            kernel_size += 1
        
        # Create elliptical structuring element
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, 
            (kernel_size, kernel_size)
        )
        
        # White top-hat: extracts bright features (beads) from dark background
        tophat = cv2.morphologyEx(current, cv2.MORPH_TOPHAT, kernel)
        
        # Combine: original + tophat boost
        # This brightens the beads relative to background
        current = cv2.add(current, tophat)
        stages["3_tophat"] = current.copy()
    else:
        stages["3_tophat"] = current.copy()
    
    # ==========================================================================
    # Stage 4: Contrast Enhancement (CLAHE)
    # ==========================================================================
    if config.get("enable_clahe", True):
        clip_limit = config.get("clahe_clip_limit", 3.0)
        tile_size = config.get("clahe_tile_grid_size", (8, 8))
        
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_size)
        current = clahe.apply(current)
        stages["4_clahe"] = current.copy()
    else:
        stages["4_clahe"] = current.copy()
    
    # ==========================================================================
    # Stage 5: Noise Reduction
    # ==========================================================================
    if config.get("enable_blur", True):
        blur_type = config.get("blur_type", "bilateral")
        
        if blur_type == "bilateral":
            diameter = config.get("blur_diameter", 7)
            sigma_color = config.get("blur_sigma_color", 75)
            sigma_space = config.get("blur_sigma_space", 75)
            current = cv2.bilateralFilter(current, diameter, sigma_color, sigma_space)
            
        elif blur_type == "gaussian":
            ksize = config.get("blur_diameter", 7)
            if ksize % 2 == 0:
                ksize += 1
            current = cv2.GaussianBlur(current, (ksize, ksize), 0)
            
        elif blur_type == "median":
            ksize = config.get("blur_diameter", 7)
            if ksize % 2 == 0:
                ksize += 1
            current = cv2.medianBlur(current, ksize)
        
        stages["5_blur"] = current.copy()
    else:
        stages["5_blur"] = current.copy()
    
    # ==========================================================================
    # Stage 6: Glare Suppression (Optional)
    # ==========================================================================
    if config.get("enable_glare_suppression", False):
        glare_threshold = config.get("glare_threshold", 245)
        glare_mode = config.get("glare_mode", "cap")
        
        if glare_mode == "cap":
            # Simple capping - limit max intensity
            current = np.clip(current, 0, glare_threshold).astype(np.uint8)
            
        elif glare_mode == "inpaint":
            # Create mask of saturated pixels
            glare_mask = (current > glare_threshold).astype(np.uint8) * 255
            # Dilate slightly to cover glare halos
            glare_mask = cv2.dilate(glare_mask, np.ones((3, 3), np.uint8), iterations=1)
            # Inpaint
            if np.any(glare_mask):
                current = cv2.inpaint(current, glare_mask, 3, cv2.INPAINT_TELEA)
        
        stages["6_glare"] = current.copy()
    else:
        stages["6_glare"] = current.copy()
    
    # Final preprocessed result
    preprocessed = current
    
    # ==========================================================================
    # Compute Quality Metrics
    # ==========================================================================
    metrics = compute_quality_metrics(original, gray, preprocessed, roi_mask)
    
    return PreprocessResult(
        original=original,
        gray=gray,
        preprocessed=preprocessed,
        stages=stages,
        metrics=metrics
    )


def compute_quality_metrics(
    original: np.ndarray,
    gray: np.ndarray,
    preprocessed: np.ndarray,
    roi_mask: Optional[np.ndarray] = None
) -> Dict[str, float]:
    """
    Compute quality metrics for preprocessing evaluation.
    
    Metrics:
    - edge_clarity: Laplacian variance (higher = sharper edges)
    - contrast_before: Std deviation of grayscale before preprocessing
    - contrast_after: Std deviation of grayscale after preprocessing
    - histogram_spread: Range of intensities used (0-255)
    - glare_pct_before: % pixels above 245 before
    - glare_pct_after: % pixels above 245 after
    """
    metrics = {}
    
    # Apply mask if provided for accurate metrics
    if roi_mask is not None:
        mask_bool = roi_mask > 127
        gray_roi = gray[mask_bool]
        preprocessed_roi = preprocessed[mask_bool]
    else:
        gray_roi = gray.flatten()
        preprocessed_roi = preprocessed.flatten()
    
    # Edge clarity (Laplacian variance)
    laplacian = cv2.Laplacian(preprocessed, cv2.CV_64F)
    if roi_mask is not None:
        laplacian_roi = laplacian[mask_bool]
    else:
        laplacian_roi = laplacian.flatten()
    metrics["edge_clarity"] = float(np.var(laplacian_roi))
    
    # Contrast metrics
    metrics["contrast_before"] = float(np.std(gray_roi)) if len(gray_roi) > 0 else 0.0
    metrics["contrast_after"] = float(np.std(preprocessed_roi)) if len(preprocessed_roi) > 0 else 0.0
    
    # Histogram spread
    if len(preprocessed_roi) > 0:
        metrics["histogram_min"] = int(np.min(preprocessed_roi))
        metrics["histogram_max"] = int(np.max(preprocessed_roi))
        metrics["histogram_spread"] = metrics["histogram_max"] - metrics["histogram_min"]
    else:
        metrics["histogram_min"] = 0
        metrics["histogram_max"] = 0
        metrics["histogram_spread"] = 0
    
    # Glare percentage
    glare_threshold = 245
    if len(gray_roi) > 0:
        metrics["glare_pct_before"] = float(np.sum(gray_roi > glare_threshold) / len(gray_roi) * 100)
    else:
        metrics["glare_pct_before"] = 0.0
        
    if len(preprocessed_roi) > 0:
        metrics["glare_pct_after"] = float(np.sum(preprocessed_roi > glare_threshold) / len(preprocessed_roi) * 100)
    else:
        metrics["glare_pct_after"] = 0.0
    
    return metrics


def create_stages_visualization(
    stages: Dict[str, np.ndarray],
    max_width: int = 1920
) -> np.ndarray:
    """
    Create a visualization showing all preprocessing stages side-by-side.
    
    Args:
        stages: Dictionary of stage name -> image
        max_width: Maximum width of output image
        
    Returns:
        Visualization image (BGR)
    """
    # Sort stages by name (which includes numeric prefix)
    sorted_stages = sorted(stages.items())
    
    # Calculate layout
    n_stages = len(sorted_stages)
    if n_stages == 0:
        return np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Use first image to get dimensions
    first_img = sorted_stages[0][1]
    h, w = first_img.shape[:2]
    
    # Calculate thumbnail size to fit max_width
    thumb_w = max_width // min(n_stages, 4)  # Max 4 per row
    scale = thumb_w / w
    thumb_h = int(h * scale)
    
    # Calculate grid
    cols = min(n_stages, 4)
    rows = (n_stages + cols - 1) // cols
    
    # Create output image
    out_h = rows * (thumb_h + 30)  # +30 for labels
    out_w = cols * thumb_w
    visualization = np.zeros((out_h, out_w, 3), dtype=np.uint8)
    
    for idx, (name, img) in enumerate(sorted_stages):
        row = idx // cols
        col = idx % cols
        
        # Resize
        thumb = cv2.resize(img, (thumb_w, thumb_h))
        
        # Convert grayscale to BGR for display
        if len(thumb.shape) == 2:
            thumb = cv2.cvtColor(thumb, cv2.COLOR_GRAY2BGR)
        
        # Position
        y_start = row * (thumb_h + 30)
        x_start = col * thumb_w
        
        # Place image
        visualization[y_start:y_start+thumb_h, x_start:x_start+thumb_w] = thumb
        
        # Add label
        label = name.replace("_", " ").title()
        cv2.putText(
            visualization, 
            label, 
            (x_start + 5, y_start + thumb_h + 20),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.4, 
            (255, 255, 255), 
            1
        )
    
    return visualization


def create_before_after_comparison(
    original: np.ndarray,
    preprocessed: np.ndarray,
    metrics: Dict[str, float],
    title: str = ""
) -> np.ndarray:
    """
    Create a side-by-side before/after comparison image.
    
    Args:
        original: Original BGR image
        preprocessed: Preprocessed grayscale image
        metrics: Quality metrics dict
        title: Optional title string
        
    Returns:
        Comparison image (BGR)
    """
    h, w = original.shape[:2]
    
    # Convert preprocessed to BGR for side-by-side
    if len(preprocessed.shape) == 2:
        preprocessed_bgr = cv2.cvtColor(preprocessed, cv2.COLOR_GRAY2BGR)
    else:
        preprocessed_bgr = preprocessed
    
    # Create side-by-side
    comparison = np.hstack([original, preprocessed_bgr])
    
    # Add labels
    cv2.putText(comparison, "Original", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
    cv2.putText(comparison, "Preprocessed", (w + 10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
    
    # Add title if provided
    if title:
        cv2.putText(comparison, title, (comparison.shape[1]//2 - 100, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    
    # Add metrics at bottom
    metrics_text = (
        f"Edge: {metrics.get('edge_clarity', 0):.0f} | "
        f"Contrast: {metrics.get('contrast_before', 0):.1f} -> {metrics.get('contrast_after', 0):.1f} | "
        f"Glare: {metrics.get('glare_pct_before', 0):.1f}% -> {metrics.get('glare_pct_after', 0):.1f}%"
    )
    cv2.putText(comparison, metrics_text, (10, comparison.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    return comparison


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
