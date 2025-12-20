"""
Unit tests for STEP-08: ResultsCache

Tests JSON caching and serialization.
"""

import pytest
import json
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mill_presenter.core.results_cache import ResultsCache
from mill_presenter.core.models import FrameDetections, Ball


def make_ball(x=100, y=100, r=20, cls=6, conf=0.75, diameter_mm=6.0):
    """Helper to create Ball."""
    return Ball(x=x, y=y, r_px=r, cls=cls, conf=conf, diameter_mm=diameter_mm)


class TestResultsCacheInit:
    """Tests for ResultsCache initialization."""
    
    def test_init_with_path(self):
        """Test initialization with file path."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            cache = ResultsCache(f.name)
            assert cache is not None
    
    def test_creates_parent_dirs(self):
        """Test that parent directories are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "subdir" / "cache.json"
            cache = ResultsCache(str(cache_path))
            cache.start_processing(100, {}, {})
            cache.finalize()
            assert cache_path.exists()


class TestCacheWriting:
    """Tests for cache write operations."""
    
    def test_start_processing(self):
        """Test start_processing initializes cache."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            cache = ResultsCache(f.name)
            cache.start_processing(
                total_frames=100,
                metadata={"fps": 30.0},
                cfg={"min_confidence": 0.5}
            )
            assert cache._frames == {}
    
    def test_append_frame(self):
        """Test appending frame detections."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            cache = ResultsCache(f.name)
            cache.start_processing(10, {}, {})
            
            frame = FrameDetections(
                frame_id=0,
                timestamp=0.0,
                balls=[make_ball()]
            )
            cache.append_frame(frame)
            
            assert 0 in cache._frames or "0" in cache._frames
    
    def test_finalize_writes_file(self):
        """Test finalize writes JSON file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        
        cache = ResultsCache(path)
        cache.start_processing(2, {"test": True}, {})
        cache.append_frame(FrameDetections(0, 0.0, [make_ball()]))
        cache.append_frame(FrameDetections(1, 0.033, [make_ball()]))
        cache.finalize()
        
        # Verify file exists and is valid JSON
        assert Path(path).exists()
        with open(path, 'r') as f:
            data = json.load(f)
        assert "frames" in data


class TestCacheReading:
    """Tests for cache read operations."""
    
    def test_load_cache(self):
        """Test loading existing cache."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode='w') as f:
            json.dump({
                "metadata": {"fps": 30},
                "config": {},
                "frames": {
                    "0": {"detections": [{"x": 100, "y": 100, "r_px": 20, "cls": 6, "conf": 0.8}]}
                }
            }, f)
            path = f.name
        
        cache = ResultsCache(path)
        cache.load()
        
        assert cache._frames is not None
    
    def test_get_frame(self):
        """Test getting detections for specific frame."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode='w') as f:
            json.dump({
                "metadata": {},
                "config": {},
                "frames": {
                    "5": {"detections": [{"x": 150, "y": 200, "r_px": 25, "cls": 8, "conf": 0.7}]}
                }
            }, f)
            path = f.name
        
        cache = ResultsCache(path)
        cache.load()
        
        detections = cache.get_frame(5)
        assert len(detections) == 1


class TestCacheRoundTrip:
    """Tests for write-then-read round trip."""
    
    def test_roundtrip_preserves_data(self):
        """Test data survives write and read."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        
        # Write
        cache = ResultsCache(path)
        cache.start_processing(1, {"test": "value"}, {})
        ball = make_ball(x=123, y=456, r=30, cls=8, conf=0.85)
        cache.append_frame(FrameDetections(0, 0.0, [ball]))
        cache.finalize()
        
        # Read
        cache2 = ResultsCache(path)
        cache2.load()
        detections = cache2.get_frame(0)
        
        assert len(detections) == 1
        det = detections[0]
        # Check key fields are preserved
        assert det.get('x') == 123 or getattr(det, 'x', None) == 123
        assert det.get('cls') == 8 or getattr(det, 'cls', None) == 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
