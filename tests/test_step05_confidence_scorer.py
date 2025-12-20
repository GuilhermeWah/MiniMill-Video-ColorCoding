"""
Unit tests for STEP-05: ConfidenceScorer

Tests multi-feature confidence scoring.
"""

import pytest
import numpy as np
import cv2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mill_presenter.core.confidence_scorer import ConfidenceScorer
from mill_presenter.core.drum_geometry import DrumGeometry
from mill_presenter.core.models import RawDetection, ScoredDetection


class TestConfidenceScorerInit:
    """Tests for ConfidenceScorer initialization."""
    
    def test_default_init(self):
        """Test default initialization."""
        scorer = ConfidenceScorer()
        assert scorer is not None
    
    def test_custom_weights(self):
        """Test initialization with custom weights."""
        cfg = {
            "edge_strength_weight": 0.4,
            "circularity_weight": 0.3,
            "interior_weight": 0.15,
            "radius_fit_weight": 0.15,
        }
        scorer = ConfidenceScorer(cfg)
        assert scorer._cfg.get("edge_strength_weight") == 0.4


class TestScoring:
    """Tests for confidence scoring."""
    
    def test_scores_detections(self):
        """Test that detections are scored."""
        # Create test image with a circle
        img = np.zeros((500, 500), dtype=np.uint8)
        cv2.circle(img, (250, 250), 40, 200, -1)
        
        raw = [
            RawDetection(x=250, y=250, r_px=40.0, source="hough")
        ]
        
        geometry = DrumGeometry(250, 250, 200, 200.0)
        scorer = ConfidenceScorer()
        
        scored = scorer.score(raw, img, geometry)
        
        assert len(scored) == 1
        assert isinstance(scored[0], ScoredDetection)
        assert 0.0 <= scored[0].conf <= 1.0
    
    def test_preserves_position(self):
        """Test that scoring preserves position info."""
        img = np.full((500, 500), 128, dtype=np.uint8)
        
        raw = [RawDetection(x=123, y=456, r_px=25.0, source="contour")]
        geometry = DrumGeometry(250, 250, 200, 200.0)
        scorer = ConfidenceScorer()
        
        scored = scorer.score(raw, img, geometry)
        
        assert scored[0].x == 123
        assert scored[0].y == 456
        assert scored[0].r_px == 25.0
    
    def test_empty_input(self):
        """Test scoring empty list."""
        img = np.zeros((100, 100), dtype=np.uint8)
        geometry = DrumGeometry(50, 50, 40, 200.0)
        scorer = ConfidenceScorer()
        
        scored = scorer.score([], img, geometry)
        
        assert scored == []
    
    def test_features_dict(self):
        """Test that features dict is populated."""
        img = np.full((500, 500), 128, dtype=np.uint8)
        cv2.circle(img, (250, 250), 30, 200, -1)
        
        raw = [RawDetection(x=250, y=250, r_px=30.0, source="hough")]
        geometry = DrumGeometry(250, 250, 200, 200.0)
        scorer = ConfidenceScorer()
        
        scored = scorer.score(raw, img, geometry)
        
        assert hasattr(scored[0], 'features')
        assert isinstance(scored[0].features, dict)


class TestConfidenceRanges:
    """Tests for confidence value ranges."""
    
    def test_confidence_in_range(self):
        """Test all confidences are in [0, 1]."""
        img = np.random.randint(50, 200, (500, 500), dtype=np.uint8)
        
        # Create several random detections
        raw = [
            RawDetection(x=np.random.randint(50, 450), 
                        y=np.random.randint(50, 450),
                        r_px=float(np.random.randint(10, 50)),
                        source="hough")
            for _ in range(10)
        ]
        
        geometry = DrumGeometry(250, 250, 200, 200.0)
        scorer = ConfidenceScorer()
        
        scored = scorer.score(raw, img, geometry)
        
        for det in scored:
            assert 0.0 <= det.conf <= 1.0, f"Confidence {det.conf} out of range"
    
    def test_clear_circle_high_confidence(self):
        """Test that clear synthetic circle gets reasonable confidence."""
        img = np.zeros((500, 500), dtype=np.uint8)
        cv2.circle(img, (250, 250), 35, 220, -1)  # Bright filled circle
        cv2.circle(img, (250, 250), 35, 250, 2)   # Strong edge
        
        raw = [RawDetection(x=250, y=250, r_px=35.0, source="hough")]
        geometry = DrumGeometry(250, 250, 200, 200.0)
        scorer = ConfidenceScorer()
        
        scored = scorer.score(raw, img, geometry)
        
        # Should have non-trivial confidence
        assert scored[0].conf > 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
