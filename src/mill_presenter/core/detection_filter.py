# MillPresenter Detection Filter

"""
4-stage filtering pipeline to reduce false positives.

Stages:
1. Rim Margin: Exclude detections in outer rim zone
2. Brightness: Reject dark holes/shadows
3. Annulus: Suppress inner holes of hollow beads
4. NMS: Non-maximum suppression for overlapping detections
"""

import cv2
import numpy as np
from typing import List, Optional

from mill_presenter.core.models import ScoredDetection
from mill_presenter.core.drum_geometry import DrumGeometry
from mill_presenter.utils import config


class DetectionFilter:
    """
    4-stage filtering pipeline for detection cleanup.
    """
    
    def __init__(self, cfg: Optional[dict] = None):
        self._cfg = cfg or config.CONFIG
    
    def filter(self, detections: List[ScoredDetection],
               geometry: DrumGeometry,
               preprocessed: np.ndarray) -> List[ScoredDetection]:
        """
        Apply full 4-stage filtering.
        
        Args:
            detections: Scored detections from ConfidenceScorer.
            geometry: Drum geometry for spatial filtering.
            preprocessed: Grayscale image for brightness check.
            
        Returns:
            Filtered detections.
        """
        # Stage 1: Rim Margin
        detections = self._filter_rim_margin(detections, geometry)
        
        # Stage 2: Brightness (hard-gate)
        detections = self._filter_brightness(detections, preprocessed)
        
        # Stage 3: Annulus rejection
        detections = self._filter_annulus(detections)
        
        # Stage 4: Confidence threshold + NMS
        detections = self._filter_confidence(detections)
        detections = self._apply_nms(detections)
        
        return detections
    
    def _filter_rim_margin(self, detections: List[ScoredDetection],
                           geometry: DrumGeometry) -> List[ScoredDetection]:
        """Stage 1: Exclude detections in outer rim zone."""
        margin = self._cfg.get("rim_margin_ratio", 0.12)
        
        result = []
        for det in detections:
            if geometry.is_inside(det.x, det.y, margin_ratio=margin):
                result.append(det)
        
        return result
    
    def _filter_brightness(self, detections: List[ScoredDetection],
                           gray: np.ndarray) -> List[ScoredDetection]:
        """Stage 2: Reject dark holes and shadows."""
        threshold = self._cfg.get("brightness_threshold", 50)
        patch_size = self._cfg.get("brightness_patch_size", 5)
        h, w = gray.shape[:2]
        
        result = []
        for det in detections:
            x, y = det.x, det.y
            half = patch_size // 2
            
            x1 = max(0, x - half)
            x2 = min(w, x + half + 1)
            y1 = max(0, y - half)
            y2 = min(h, y + half + 1)
            
            if x2 > x1 and y2 > y1:
                patch = gray[y1:y2, x1:x2]
                mean_brightness = np.mean(patch)
                
                if mean_brightness >= threshold:
                    result.append(det)
            else:
                # Edge case: keep if we can't sample
                result.append(det)
        
        return result
    
    def _filter_annulus(self, detections: List[ScoredDetection]) -> List[ScoredDetection]:
        """Stage 3: Suppress inner holes of hollow beads."""
        if len(detections) < 2:
            return detections
        
        # Sort by radius descending (process larger first)
        sorted_dets = sorted(detections, key=lambda d: d.r_px, reverse=True)
        
        keep = [True] * len(sorted_dets)
        
        for i in range(len(sorted_dets)):
            if not keep[i]:
                continue
            
            large = sorted_dets[i]
            
            for j in range(i + 1, len(sorted_dets)):
                if not keep[j]:
                    continue
                
                small = sorted_dets[j]
                
                # Check if small is inside large (potential inner hole)
                dx = small.x - large.x
                dy = small.y - large.y
                dist = np.sqrt(dx*dx + dy*dy)
                
                # Inner hole test: centered inside and smaller radius
                if dist < large.r_px * 0.5 and small.r_px < large.r_px * 0.8:
                    keep[j] = False
        
        return [d for d, k in zip(sorted_dets, keep) if k]
    
    def _filter_confidence(self, detections: List[ScoredDetection]) -> List[ScoredDetection]:
        """Apply confidence threshold."""
        min_conf = self._cfg.get("min_confidence", 0.5)
        return [d for d in detections if d.conf >= min_conf]
    
    def _apply_nms(self, detections: List[ScoredDetection]) -> List[ScoredDetection]:
        """Stage 4: Non-maximum suppression for overlapping circles."""
        if len(detections) < 2:
            return detections
        
        overlap_thresh = self._cfg.get("nms_overlap_threshold", 0.5)
        
        # Sort by confidence descending
        sorted_dets = sorted(detections, key=lambda d: d.conf, reverse=True)
        
        keep = []
        for det in sorted_dets:
            is_duplicate = False
            
            for kept in keep:
                # Calculate overlap as distance / combined radii
                dx = det.x - kept.x
                dy = det.y - kept.y
                dist = np.sqrt(dx*dx + dy*dy)
                combined_r = det.r_px + kept.r_px
                
                overlap = 1.0 - (dist / combined_r) if combined_r > 0 else 0
                
                if overlap > overlap_thresh:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                keep.append(det)
        
        return keep
