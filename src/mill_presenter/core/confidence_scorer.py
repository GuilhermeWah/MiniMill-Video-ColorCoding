# MillPresenter Confidence Scorer

"""
Multi-feature confidence scoring for circle detections.
Assigns a confidence score [0.0, 1.0] based on 4 weighted features.

Features:
- Edge Strength (35%): Gradient magnitude along perimeter
- Circularity (25%): Edge consistency around the circle
- Interior Uniformity (20%): Brightness pattern inside
- Radius Fit (20%): Match to expected bead size range
"""

import cv2
import numpy as np
import math
from typing import List, Dict, Optional

from mill_presenter.core.models import RawDetection, ScoredDetection
from mill_presenter.core.drum_geometry import DrumGeometry
from mill_presenter.utils import config


class ConfidenceScorer:
    """
    Scores each raw detection with a weighted multi-feature confidence.
    """
    
    def __init__(self, cfg: Optional[dict] = None):
        self._cfg = cfg or config.CONFIG
        self._grad_x: Optional[np.ndarray] = None
        self._grad_y: Optional[np.ndarray] = None
        self._grad_mag: Optional[np.ndarray] = None
    
    def score(self, detections: List[RawDetection], 
              preprocessed: np.ndarray,
              geometry: DrumGeometry) -> List[ScoredDetection]:
        """
        Score all detections.
        
        Args:
            detections: Raw detections from VisionProcessor.
            preprocessed: Grayscale preprocessed image.
            geometry: Drum geometry for radius reference.
            
        Returns:
            List of scored detections.
        """
        # Precompute gradients
        self._compute_gradients(preprocessed)
        
        # Get radius bounds for radius_fit scoring
        min_r, max_r = self._get_radius_bounds(geometry)
        
        scored = []
        for det in detections:
            features = self._compute_features(det, preprocessed, min_r, max_r)
            conf = self._weighted_score(features)
            
            scored.append(ScoredDetection(
                x=det.x,
                y=det.y,
                r_px=det.r_px,
                conf=conf,
                features=features
            ))
        
        return scored
    
    def _compute_gradients(self, gray: np.ndarray) -> None:
        """Precompute image gradients."""
        sigma = self._cfg.get("edge_gradient_sigma", 1.0)
        ksize = max(3, int(sigma * 4) | 1)  # Ensure odd
        
        self._grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=ksize)
        self._grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=ksize)
        self._grad_mag = np.sqrt(self._grad_x**2 + self._grad_y**2)
    
    def _get_radius_bounds(self, geometry: DrumGeometry) -> tuple:
        px_per_mm = geometry.px_per_mm
        min_mm = self._cfg.get("min_bead_diameter_mm", 3.0) / 2.0
        max_mm = self._cfg.get("max_bead_diameter_mm", 12.0) / 2.0
        return min_mm * px_per_mm, max_mm * px_per_mm
    
    def _compute_features(self, det: RawDetection, gray: np.ndarray,
                          min_r: float, max_r: float) -> Dict[str, float]:
        """Compute all 4 features for a detection."""
        x, y, r = det.x, det.y, det.r_px
        h, w = gray.shape[:2]
        
        # Sample points around perimeter
        n_samples = self._cfg.get("edge_sample_points", 36)
        angles = np.linspace(0, 2 * math.pi, n_samples, endpoint=False)
        
        edge_values = []
        for angle in angles:
            px = int(x + r * math.cos(angle))
            py = int(y + r * math.sin(angle))
            
            if 0 <= px < w and 0 <= py < h:
                edge_values.append(self._grad_mag[py, px])
        
        # Edge Strength: normalized mean gradient
        if edge_values:
            mean_grad = np.mean(edge_values)
            # Normalize to [0, 1] (empirical max ~100 for typical images)
            edge_strength = min(1.0, mean_grad / 100.0)
        else:
            edge_strength = 0.0
        
        # Circularity: consistency of edge (1 - coefficient of variation)
        if edge_values and np.mean(edge_values) > 0:
            cv = np.std(edge_values) / np.mean(edge_values)
            circularity = max(0.0, 1.0 - cv)
        else:
            circularity = 0.0
        
        # Interior Uniformity: brightness pattern
        interior = self._compute_interior_uniformity(gray, x, y, r)
        
        # Radius Fit: how well the radius fits expected range
        if r <= min_r:
            radius_fit = 0.0
        elif r >= max_r:
            radius_fit = 0.0
        else:
            # Optimal at center of range [0.2, 0.8]
            norm_r = (r - min_r) / (max_r - min_r)
            if 0.2 <= norm_r <= 0.8:
                radius_fit = 1.0
            elif norm_r < 0.2:
                radius_fit = norm_r / 0.2
            else:
                radius_fit = (1.0 - norm_r) / 0.2
        
        return {
            "edge_strength": edge_strength,
            "circularity": circularity,
            "interior": interior,
            "radius_fit": radius_fit
        }
    
    def _compute_interior_uniformity(self, gray: np.ndarray, 
                                     x: int, y: int, r: float) -> float:
        """Compute interior uniformity score."""
        h, w = gray.shape[:2]
        sample_r = int(r * self._cfg.get("interior_sample_ratio", 0.7))
        
        # Sample interior region
        x1 = max(0, x - sample_r)
        x2 = min(w, x + sample_r)
        y1 = max(0, y - sample_r)
        y2 = min(h, y + sample_r)
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        patch = gray[y1:y2, x1:x2]
        
        # Metallic beads should have moderate brightness
        mean_int = np.mean(patch)
        std_int = np.std(patch)
        
        # Score based on brightness (not too dark, not saturated)
        brightness_score = min(mean_int / 128.0, 1.0) * min((255 - mean_int) / 128.0, 1.0)
        
        # Uniformity based on low variance
        uniformity = max(0.0, 1.0 - std_int / 50.0)
        
        return 0.6 * brightness_score + 0.4 * uniformity
    
    def _weighted_score(self, features: Dict[str, float]) -> float:
        """Compute weighted confidence score."""
        w_edge = self._cfg.get("weight_edge_strength", 0.35)
        w_circ = self._cfg.get("weight_circularity", 0.25)
        w_int = self._cfg.get("weight_interior", 0.20)
        w_rad = self._cfg.get("weight_radius_fit", 0.20)
        
        score = (
            w_edge * features["edge_strength"] +
            w_circ * features["circularity"] +
            w_int * features["interior"] +
            w_rad * features["radius_fit"]
        )
        
        return max(0.0, min(1.0, score))
