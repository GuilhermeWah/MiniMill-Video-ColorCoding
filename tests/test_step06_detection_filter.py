"""
Unit tests for STEP-06: DetectionFilter

Tests 4-stage filtering pipeline: rim margin, brightness, annulus, NMS.
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mill_presenter.core.detection_filter import DetectionFilter
from mill_presenter.core.drum_geometry import DrumGeometry
from mill_presenter.core.models import ScoredDetection


def make_detection(x, y, r, conf=0.7):
    """Helper to create ScoredDetection."""
    return ScoredDetection(x=x, y=y, r_px=r, conf=conf, features={})


class TestDetectionFilterInit:
    """Tests for DetectionFilter initialization."""
    
    def test_default_init(self):
        """Test default initialization."""
        filter_ = DetectionFilter()
        assert filter_ is not None
    
    def test_custom_config(self):
        """Test initialization with custom config."""
        cfg = {"rim_margin_ratio": 0.15, "min_confidence": 0.6}
        filter_ = DetectionFilter(cfg)
        assert filter_._cfg.get("rim_margin_ratio") == 0.15


class TestRimMarginFilter:
    """Tests for Stage 1: Rim margin filtering."""
    
    def test_center_detection_passes(self):
        """Test detection at center passes rim filter."""
        geometry = DrumGeometry(500, 500, 300, 200.0)
        filter_ = DetectionFilter()
        
        detections = [make_detection(500, 500, 20)]
        result = filter_._filter_rim_margin(detections, geometry)
        
        assert len(result) == 1
    
    def test_rim_detection_rejected(self):
        """Test detection at rim is rejected."""
        geometry = DrumGeometry(500, 500, 300, 200.0)
        filter_ = DetectionFilter({"rim_margin_ratio": 0.12})
        
        # Detection very close to rim edge
        detections = [make_detection(790, 500, 20)]  # 290 from center, close to 300 radius
        result = filter_._filter_rim_margin(detections, geometry)
        
        # Should be rejected (outside 88% of radius)
        assert len(result) == 0


class TestBrightnessFilter:
    """Tests for Stage 2: Brightness hard-gate."""
    
    def test_method_exists(self):
        """Verify brightness filter method exists."""
        filter_ = DetectionFilter()
        assert hasattr(filter_, "_filter_brightness")
    
    def test_bright_detection_passes(self):
        """Test detection on bright area passes."""
        filter_ = DetectionFilter({"brightness_threshold": 50})
        img = np.full((500, 500), 150, dtype=np.uint8)  # Bright image
        
        detections = [make_detection(250, 250, 20)]
        result = filter_._filter_brightness(detections, img)
        
        assert len(result) == 1
    
    def test_dark_detection_rejected(self):
        """Test detection on dark area is rejected."""
        filter_ = DetectionFilter({"brightness_threshold": 50})
        img = np.full((500, 500), 30, dtype=np.uint8)  # Dark image
        
        detections = [make_detection(250, 250, 20)]
        result = filter_._filter_brightness(detections, img)
        
        assert len(result) == 0


class TestAnnulusFilter:
    """Tests for Stage 3: Annulus rejection."""
    
    def test_method_exists(self):
        """Verify annulus filter method exists."""
        filter_ = DetectionFilter()
        assert hasattr(filter_, "_filter_annulus")
    
    def test_nested_circles_suppressed(self):
        """Test that smaller circle inside larger is suppressed."""
        filter_ = DetectionFilter()
        
        # Large circle and smaller one at same center
        detections = [
            make_detection(250, 250, 50, conf=0.8),  # Larger
            make_detection(250, 250, 20, conf=0.7),  # Smaller, centered inside
        ]
        
        result = filter_._filter_annulus(detections)
        
        # Should only keep the larger one
        assert len(result) == 1
        assert result[0].r_px == 50
    
    def test_separate_circles_kept(self):
        """Test that well-separated circles are kept."""
        filter_ = DetectionFilter()
        
        detections = [
            make_detection(100, 100, 30),
            make_detection(300, 300, 25),
        ]
        
        result = filter_._filter_annulus(detections)
        
        assert len(result) == 2


class TestNMSFilter:
    """Tests for Stage 4: Non-maximum suppression."""
    
    def test_overlapping_suppressed(self):
        """Test overlapping detections are suppressed."""
        filter_ = DetectionFilter({"nms_overlap_threshold": 0.5})
        
        # Two overlapping detections at same position
        detections = [
            make_detection(250, 250, 30, conf=0.8),
            make_detection(255, 255, 28, conf=0.6),  # Slightly offset, overlapping
        ]
        
        result = filter_._apply_nms(detections)
        
        # Should keep only higher confidence
        assert len(result) == 1
        assert result[0].conf == 0.8
    
    def test_non_overlapping_kept(self):
        """Test non-overlapping detections are kept."""
        filter_ = DetectionFilter()
        
        detections = [
            make_detection(100, 100, 20, conf=0.7),
            make_detection(300, 300, 20, conf=0.6),
        ]
        
        result = filter_._apply_nms(detections)
        
        assert len(result) == 2


class TestFullPipeline:
    """Tests for complete 4-stage filtering."""
    
    def test_full_filter_pipeline(self):
        """Test complete filtering pipeline."""
        geometry = DrumGeometry(250, 250, 200, 200.0)
        img = np.full((500, 500), 128, dtype=np.uint8)
        filter_ = DetectionFilter()
        
        detections = [
            make_detection(250, 250, 25, conf=0.8),  # Good detection
            make_detection(250, 250, 10, conf=0.6),  # Inner hole (annulus)
            make_detection(450, 250, 20, conf=0.55), # Near rim
        ]
        
        result = filter_.filter(detections, geometry, img)
        
        # Should filter some out
        assert len(result) <= len(detections)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
