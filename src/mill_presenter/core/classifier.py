# MillPresenter Classifier

"""
Size classification for detected beads.
Converts pixel radius to mm diameter and assigns size class.
"""

from typing import List, Optional

from mill_presenter.core.models import ScoredDetection, Ball
from mill_presenter.utils import config


class Classifier:
    """
    Bead size classifier.
    Converts pixel measurements to physical dimensions and bins into classes.
    """
    
    def __init__(self, bins_mm: Optional[List[dict]] = None):
        """
        Initialize classifier with size bins.
        
        Args:
            bins_mm: List of {"label": int, "min": float, "max": float}.
                     If None, uses config default.
        """
        if bins_mm is None:
            bins_mm = config.get("bins_mm", [
                {"label": 4, "min": 3.0, "max": 5.0},
                {"label": 6, "min": 5.0, "max": 7.0},
                {"label": 8, "min": 7.0, "max": 9.0},
                {"label": 10, "min": 9.0, "max": 12.0},
            ])
        
        self._bins = bins_mm
    
    def classify(self, detections: List[ScoredDetection],
                 px_per_mm: float) -> List[Ball]:
        """
        Classify all detections.
        
        Args:
            detections: Filtered scored detections.
            px_per_mm: Calibration factor from DrumGeometry.
            
        Returns:
            List of classified Ball objects.
        """
        balls = []
        
        for det in detections:
            diameter_mm = (2 * det.r_px) / px_per_mm
            cls = self._get_class(diameter_mm)
            
            balls.append(Ball(
                x=det.x,
                y=det.y,
                r_px=det.r_px,
                diameter_mm=diameter_mm,
                cls=cls,
                conf=det.conf
            ))
        
        return balls
    
    def _get_class(self, diameter_mm: float) -> int:
        """
        Determine size class for a given diameter.
        
        Returns:
            Class label (4, 6, 8, 10) or 0 for unknown.
        """
        for bin_def in self._bins:
            if bin_def["min"] <= diameter_mm < bin_def["max"]:
                return bin_def["label"]
        
        return 0  # Unknown
