"""
Unit tests for STEP-07: Classifier

Tests size bin classification.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mill_presenter.core.classifier import Classifier
from mill_presenter.core.models import ScoredDetection, Ball


def make_scored(x, y, r_px, conf=0.7):
    """Helper to create ScoredDetection."""
    return ScoredDetection(x=x, y=y, r_px=r_px, conf=conf, features={})


class TestClassifierInit:
    """Tests for Classifier initialization."""
    
    def test_default_init(self):
        """Test default initialization."""
        classifier = Classifier()
        assert classifier is not None
    
    def test_custom_bins(self):
        """Test initialization with custom bin ranges."""
        classifier = Classifier()
        assert hasattr(classifier, '_bin_ranges') or hasattr(classifier, '_cfg')


class TestDiameterConversion:
    """Tests for pixel to mm conversion."""
    
    def test_diameter_calculation(self):
        """Test diameter_mm calculation."""
        classifier = Classifier()
        
        px_per_mm = 4.0
        r_px = 12.0  # radius in pixels
        
        # Expected diameter: 2 * 12 / 4 = 6mm
        expected = 6.0
        
        # Classify and check
        scored = [make_scored(100, 100, r_px)]
        balls = classifier.classify(scored, px_per_mm)
        
        assert len(balls) == 1
        assert abs(balls[0].diameter_mm - expected) < 0.1


class TestSizeBinning:
    """Tests for size class assignment."""
    
    def test_4mm_class(self):
        """Test detection classified as 4mm."""
        classifier = Classifier()
        px_per_mm = 4.0
        
        # 4mm bead: diameter 3-5mm, so radius 6-10px at 4px/mm
        scored = [make_scored(100, 100, r_px=8.0)]  # 8px radius = 4mm diameter
        balls = classifier.classify(scored, px_per_mm)
        
        assert balls[0].cls == 4
    
    def test_6mm_class(self):
        """Test detection classified as 6mm."""
        classifier = Classifier()
        px_per_mm = 4.0
        
        # 6mm bead: diameter 5-7mm, so radius 10-14px at 4px/mm
        scored = [make_scored(100, 100, r_px=12.0)]  # 12px radius = 6mm diameter
        balls = classifier.classify(scored, px_per_mm)
        
        assert balls[0].cls == 6
    
    def test_8mm_class(self):
        """Test detection classified as 8mm."""
        classifier = Classifier()
        px_per_mm = 4.0
        
        # 8mm bead: diameter 7-9mm, so radius 14-18px at 4px/mm
        scored = [make_scored(100, 100, r_px=16.0)]  # 16px radius = 8mm diameter
        balls = classifier.classify(scored, px_per_mm)
        
        assert balls[0].cls == 8
    
    def test_10mm_class(self):
        """Test detection classified as 10mm."""
        classifier = Classifier()
        px_per_mm = 4.0
        
        # 10mm bead: diameter 9-12mm, so radius 18-24px at 4px/mm
        scored = [make_scored(100, 100, r_px=20.0)]  # 20px radius = 10mm diameter
        balls = classifier.classify(scored, px_per_mm)
        
        assert balls[0].cls == 10
    
    def test_unknown_class(self):
        """Test out-of-range detection classified as 0 (unknown)."""
        classifier = Classifier()
        px_per_mm = 4.0
        
        # Very small: 1mm diameter
        scored = [make_scored(100, 100, r_px=2.0)]  # 2px radius = 1mm diameter
        balls = classifier.classify(scored, px_per_mm)
        
        assert balls[0].cls == 0


class TestBallOutput:
    """Tests for Ball dataclass output."""
    
    def test_ball_has_required_fields(self):
        """Test Ball has all required fields."""
        classifier = Classifier()
        
        scored = [make_scored(123, 456, r_px=15.0, conf=0.85)]
        balls = classifier.classify(scored, px_per_mm=4.0)
        
        ball = balls[0]
        assert isinstance(ball, Ball)
        assert ball.x == 123
        assert ball.y == 456
        assert ball.r_px == 15.0
        assert ball.conf == 0.85
        assert hasattr(ball, 'cls')
        assert hasattr(ball, 'diameter_mm')
    
    def test_empty_input(self):
        """Test classification of empty list."""
        classifier = Classifier()
        
        balls = classifier.classify([], px_per_mm=4.0)
        
        assert balls == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
