# MillPresenter Preprocessor

"""
Image preprocessing pipeline for detection enhancement.
Prepares frames for optimal HoughCircles and contour detection.

Pipeline (matches legacy):
1. Grayscale conversion
2. ROI masking (optional)
3. Bilateral filter (edge-preserving smoothing)
4. CLAHE (local contrast enhancement)
"""

import cv2
import numpy as np
from typing import Optional, Dict, Any

from mill_presenter.utils import config


class Preprocessor:
    """
    Preprocessing pipeline for bead detection (legacy-compatible).
    
    All stages are applied in sequence. Each stage is individually
    configurable via the config module.
    """
    
    def __init__(self, cfg: Optional[Dict[str, Any]] = None):
        """
        Initialize preprocessor with configuration.
        
        Args:
            cfg: Optional config override. If None, uses global config.
        """
        self._cfg = cfg or config.CONFIG
        
        # Cache CLAHE instance
        clip = self._cfg.get("clahe_clip_limit", 2.0)
        tile = self._cfg.get("clahe_tile_size", 8)
        self._clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(tile, tile))
    
    def process(self, frame_bgr: np.ndarray, 
                roi_mask: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Run the preprocessing pipeline (matches legacy order).
        
        Legacy pipeline: Grayscale → Bilateral → CLAHE
        Optional: ROI masking if mask provided.
        
        Args:
            frame_bgr: Input BGR frame.
            roi_mask: Optional ROI mask (255=inside, 0=outside).
            
        Returns:
            Preprocessed grayscale image ready for detection.
        """
        # Stage 1: Grayscale
        gray = self._to_grayscale(frame_bgr)
        
        # Stage 2: ROI Masking (optional)
        if roi_mask is not None:
            gray = self._apply_roi_mask(gray, roi_mask)
        
        # Stage 3: Bilateral filter (edge-preserving smoothing)
        gray = self._apply_bilateral(gray)
        
        # Stage 4: CLAHE (local contrast enhancement)
        gray = self._apply_clahe(gray)
        
        return gray
    
    def _to_grayscale(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Stage 1: Convert to grayscale."""
        return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    
    def _apply_roi_mask(self, gray: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Stage 2: Zero pixels outside ROI."""
        return cv2.bitwise_and(gray, gray, mask=mask)
    
    def _apply_tophat(self, gray: np.ndarray) -> np.ndarray:
        """Stage 3: Top-hat transform for illumination normalization."""
        kernel_size = self._cfg.get("tophat_kernel_size", 15)
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
        )
        
        # White top-hat: bright objects on dark background
        tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
        
        # Blend with original for natural look
        # Normalize tophat to [0, 255] and blend
        return cv2.add(gray, tophat)
    
    def _apply_clahe(self, gray: np.ndarray) -> np.ndarray:
        """Stage 4: CLAHE for local contrast enhancement."""
        return self._clahe.apply(gray)
    
    def _apply_bilateral(self, gray: np.ndarray) -> np.ndarray:
        """Bilateral filter for edge-preserving smoothing."""
        # d=5 is faster than d=9 while still effective
        d = self._cfg.get("bilateral_d", 5)
        sigma_color = self._cfg.get("bilateral_sigma_color", 75)
        sigma_space = self._cfg.get("bilateral_sigma_space", 75)
        
        return cv2.bilateralFilter(gray, d, sigma_color, sigma_space)
    
    def _suppress_glare(self, gray: np.ndarray) -> np.ndarray:
        """Stage 6: Suppress glare (saturated bright regions)."""
        threshold = self._cfg.get("glare_threshold", 250)
        replacement = self._cfg.get("glare_replacement", 200)
        
        # Clamp values above threshold
        result = gray.copy()
        result[result > threshold] = replacement
        
        return result
