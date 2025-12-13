"""
Confidence scoring module for MillPresenter pipeline.

STEP_05: Confidence Scoring

This module assigns confidence scores [0.0, 1.0] to each detection.
Confidence is computed from observable image evidence only.

Features:
- Edge strength along circumference
- Circularity (edge consistency)
- Interior uniformity
- Radius fit to expected sizes
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import math


@dataclass
class ScoredDetection:
    """A detection with confidence score."""
    x: int
    y: int
    r_px: float
    conf: float
    features: Dict[str, float]  # Individual feature scores
    
    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "r_px": round(self.r_px, 2),
            "conf": round(self.conf, 3),
            "features": {k: round(v, 3) for k, v in self.features.items()}
        }


def precompute_gradient(gray: np.ndarray) -> np.ndarray:
    """Compute gradient magnitude once for the entire frame."""
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    return np.sqrt(grad_x**2 + grad_y**2)


def compute_edge_strength(
    grad_mag: np.ndarray,
    x: int, y: int, r: float,
    n_points: int = 36
) -> float:
    """
    Compute average gradient magnitude along circle perimeter.
    
    Args:
        grad_mag: Pre-computed gradient magnitude image
        
    Returns normalized score [0, 1].
    """
    h, w = grad_mag.shape[:2]
    
    # Sample points around circumference
    angles = np.linspace(0, 2*np.pi, n_points, endpoint=False)
    samples = []
    
    for angle in angles:
        px = int(round(x + r * np.cos(angle)))
        py = int(round(y + r * np.sin(angle)))
        
        # Check bounds
        if 0 <= px < w and 0 <= py < h:
            samples.append(grad_mag[py, px])
    
    if len(samples) < n_points * 0.5:
        return 0.0  # Too few valid samples
    
    # Average gradient magnitude, normalized
    avg_grad = np.mean(samples)
    # Normalize: typical edge gradient is ~50-150, saturate at 200
    normalized = min(avg_grad / 150.0, 1.0)
    
    return float(normalized)


def compute_circularity(
    grad_mag: np.ndarray,
    x: int, y: int, r: float,
    n_points: int = 36
) -> float:
    """
    Compute edge consistency around perimeter.
    Low variance = good circularity.
    
    Args:
        grad_mag: Pre-computed gradient magnitude image
    
    Returns normalized score [0, 1].
    """
    h, w = grad_mag.shape[:2]
    
    # Sample points around circumference
    angles = np.linspace(0, 2*np.pi, n_points, endpoint=False)
    samples = []
    
    for angle in angles:
        px = int(round(x + r * np.cos(angle)))
        py = int(round(y + r * np.sin(angle)))
        
        if 0 <= px < w and 0 <= py < h:
            samples.append(grad_mag[py, px])
    
    if len(samples) < n_points * 0.5:
        return 0.0
    
    # Coefficient of variation (std / mean)
    mean_val = np.mean(samples)
    if mean_val < 1e-6:
        return 0.0
    
    cv = np.std(samples) / mean_val
    
    # Lower CV = better circularity
    # CV of 0 = perfect, CV > 1 = very inconsistent
    score = max(0, 1.0 - cv)
    
    return float(score)


def compute_interior_uniformity(
    gray: np.ndarray,
    x: int, y: int, r: float,
    sample_ratio: float = 0.7
) -> float:
    """
    Analyze intensity pattern inside circle.
    Real beads have characteristic bright center pattern.
    
    Returns normalized score [0, 1].
    """
    h, w = gray.shape[:2]
    
    # Sample interior pixels
    inner_r = int(r * sample_ratio)
    if inner_r < 2:
        return 0.5  # Too small to analyze
    
    # Create mask for interior
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, (x, y), inner_r, 255, -1)
    
    # Get interior pixels
    interior_pixels = gray[mask > 0]
    
    if len(interior_pixels) < 10:
        return 0.5
    
    # Analyze intensity distribution
    mean_int = np.mean(interior_pixels)
    std_int = np.std(interior_pixels)
    
    # Beads typically have:
    # - Moderate to high mean intensity (metallic, reflective)
    # - Some variation (specular highlights, shadows)
    
    # Penalize very low intensity (shadows/holes)
    intensity_score = min(mean_int / 128.0, 1.0)
    
    # Penalize very high variance (noise) or very low (flat areas)
    # Optimal std is around 20-50
    if std_int < 10:
        variance_score = std_int / 10.0  # Too uniform
    elif std_int > 60:
        variance_score = max(0, 1.0 - (std_int - 60) / 60.0)  # Too noisy
    else:
        variance_score = 1.0  # Good range
    
    return float(0.6 * intensity_score + 0.4 * variance_score)


def compute_radius_fit(
    r: float,
    min_radius: int,
    max_radius: int
) -> float:
    """
    Score how well the radius fits expected bead sizes.
    
    Returns normalized score [0, 1].
    """
    # Optimal range is middle 60% of the detection range
    range_size = max_radius - min_radius
    optimal_min = min_radius + range_size * 0.2
    optimal_max = max_radius - range_size * 0.2
    
    if optimal_min <= r <= optimal_max:
        return 1.0
    elif r < min_radius or r > max_radius:
        return 0.0
    elif r < optimal_min:
        # Scale from 0 at min_radius to 1 at optimal_min
        return (r - min_radius) / (optimal_min - min_radius)
    else:
        # Scale from 1 at optimal_max to 0 at max_radius
        return (max_radius - r) / (max_radius - optimal_max)


def score_detection(
    gray: np.ndarray,
    grad_mag: np.ndarray,
    x: int, y: int, r: float,
    min_radius: int,
    max_radius: int,
    config: Dict[str, Any]
) -> Tuple[float, Dict[str, float]]:
    """
    Compute confidence score for a single detection.
    
    Args:
        gray: Grayscale image (for interior analysis)
        grad_mag: Pre-computed gradient magnitude image
        
    Returns (confidence, feature_dict).
    """
    # Extract weights
    w_edge = config.get("weight_edge_strength", 0.35)
    w_circ = config.get("weight_circularity", 0.25)
    w_int = config.get("weight_interior", 0.20)
    w_rad = config.get("weight_radius_fit", 0.20)
    
    n_points = config.get("edge_sample_points", 36)
    sample_ratio = config.get("interior_sample_ratio", 0.7)
    
    # Compute features using pre-computed gradient
    edge_strength = compute_edge_strength(grad_mag, x, y, r, n_points)
    circularity = compute_circularity(grad_mag, x, y, r, n_points)
    interior = compute_interior_uniformity(gray, x, y, r, sample_ratio)
    radius_fit = compute_radius_fit(r, min_radius, max_radius)
    
    # Weighted sum
    conf = (w_edge * edge_strength + 
            w_circ * circularity + 
            w_int * interior + 
            w_rad * radius_fit)
    
    # Clamp to [0, 1]
    conf = max(0.0, min(1.0, conf))
    
    features = {
        "edge_strength": edge_strength,
        "circularity": circularity,
        "interior": interior,
        "radius_fit": radius_fit
    }
    
    return conf, features


def score_detections(
    gray: np.ndarray,
    detections: List[Dict],
    drum_radius_px: int,
    config: Optional[Dict[str, Any]] = None
) -> List[ScoredDetection]:
    """
    Score all detections in a frame.
    
    Args:
        gray: Grayscale frame
        detections: List of detection dicts with x, y, r_px
        drum_radius_px: Drum radius for radius range calculation
        config: Confidence configuration
        
    Returns:
        List of ScoredDetection objects
    """
    from config import CONFIDENCE_CONFIG, DETECTION_BEAD_CONFIG
    
    if config is None:
        config = CONFIDENCE_CONFIG.copy()
    
    # Get radius range from detection config
    from detect import calculate_radius_range
    min_r, max_r = calculate_radius_range(drum_radius_px, DETECTION_BEAD_CONFIG)
    
    # Precompute gradient magnitude ONCE for the entire frame
    grad_mag = precompute_gradient(gray)
    
    scored = []
    for det in detections:
        x, y, r = det["x"], det["y"], det["r_px"]
        
        conf, features = score_detection(
            gray, grad_mag, x, y, r, min_r, max_r, config
        )
        
        scored.append(ScoredDetection(
            x=x, y=y, r_px=r, conf=conf, features=features
        ))
    
    return scored


def create_confidence_overlay(
    frame: np.ndarray,
    scored_detections: List[ScoredDetection],
    thickness: int = 2
) -> np.ndarray:
    """
    Create visualization with confidence-based color and opacity.
    
    High confidence: Green, solid
    Medium confidence: Yellow, semi-transparent
    Low confidence: Red, faint
    """
    # Ensure BGR
    if len(frame.shape) == 2:
        base = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    else:
        base = frame.copy()
    
    # Create overlay layer for blending
    overlay = base.copy()
    
    for det in scored_detections:
        conf = det.conf
        
        # Color based on confidence (BGR)
        if conf >= 0.7:
            color = (0, 255, 0)  # Green
        elif conf >= 0.4:
            # Interpolate yellow to orange
            t = (conf - 0.4) / 0.3
            color = (0, int(200 + 55*t), 255)  # Orange to Yellow
        else:
            color = (0, 0, 255)  # Red
        
        # Draw on overlay
        cv2.circle(overlay, (det.x, det.y), int(det.r_px), color, thickness)
        cv2.circle(overlay, (det.x, det.y), 2, color, -1)
    
    # Blend with opacity based on confidence
    # For simplicity, use uniform blend here; per-detection opacity is complex
    # We achieve visual effect through color intensity instead
    alpha = 0.8
    result = cv2.addWeighted(overlay, alpha, base, 1 - alpha, 0)
    
    # Add stats
    high_conf = sum(1 for d in scored_detections if d.conf >= 0.7)
    med_conf = sum(1 for d in scored_detections if 0.4 <= d.conf < 0.7)
    low_conf = sum(1 for d in scored_detections if d.conf < 0.4)
    
    h = result.shape[0]
    cv2.putText(result, f"High (>=0.7): {high_conf}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(result, f"Med (0.4-0.7): {med_conf}", (10, 55),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
    cv2.putText(result, f"Low (<0.4): {low_conf}", (10, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
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
