# MillPresenter — Overlay Painter (STEP-13)

"""
Draws detection overlays on video frames.

Features:
- Circle overlays for ball detections
- Color-coded by size class (4mm, 6mm, 8mm, 10mm)
- Confidence-based filtering
- Class visibility toggles
- Label rendering
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import cv2


# Color palette for size classes (BGR format for OpenCV)
CLASS_COLORS_BGR = {
    4: (106, 206, 158),   # Green - 4mm
    6: (247, 162, 122),   # Blue - 6mm  
    8: (104, 175, 224),   # Orange - 8mm
    10: (142, 118, 247),  # Red/Pink - 10mm
}

# Fallback color
DEFAULT_COLOR_BGR = (200, 200, 200)


class OverlayPainter:
    """
    Paints detection overlays onto video frames.
    
    Usage:
        painter = OverlayPainter()
        painter.set_detections(frame_detections)
        painted_frame = painter.paint(frame_bgr)
    """
    
    def __init__(self):
        # Current frame detections
        self._detections: List[Dict] = []
        
        # Visibility settings
        self._visible_classes: Dict[int, bool] = {4: True, 6: True, 8: True, 10: True}
        self._min_confidence: float = 0.5
        
        # Rendering options
        self._show_labels: bool = False
        self._circle_thickness: int = 2
        self._label_font_scale: float = 0.5
    
    # ========================================================================
    # Configuration
    # ========================================================================
    
    def set_class_visible(self, class_mm: int, visible: bool) -> None:
        """Set visibility for a size class."""
        if class_mm in self._visible_classes:
            self._visible_classes[class_mm] = visible
    
    def set_min_confidence(self, confidence: float) -> None:
        """Set minimum confidence threshold for display."""
        self._min_confidence = max(0.0, min(1.0, confidence))
    
    def set_show_labels(self, show: bool) -> None:
        """Toggle label display."""
        self._show_labels = show
    
    def set_circle_thickness(self, thickness: int) -> None:
        """Set circle line thickness."""
        self._circle_thickness = max(1, min(5, thickness))
    
    # ========================================================================
    # Detection data
    # ========================================================================
    
    def set_detections(self, detections: List[Dict]) -> None:
        """
        Set detections for the current frame.
        
        Each detection should have:
        - x, y: center coordinates
        - radius or r_px: circle radius
        - class_mm: size class (4, 6, 8, 10)
        - confidence: detection confidence (0.0 to 1.0)
        """
        self._detections = detections or []
    
    def clear_detections(self) -> None:
        """Clear current detections."""
        self._detections = []
    
    # ========================================================================
    # Rendering
    # ========================================================================
    
    def paint(self, frame_bgr: np.ndarray) -> np.ndarray:
        """
        Paint overlays onto a frame.
        
        Args:
            frame_bgr: Input frame in BGR format (will be modified in-place)
        
        Returns:
            Frame with overlays painted
        """
        if not self._detections:
            return frame_bgr
        
        for det in self._detections:
            self._paint_detection(frame_bgr, det)
        
        return frame_bgr
    
    def paint_copy(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Paint overlays onto a copy of the frame (original unchanged)."""
        return self.paint(frame_bgr.copy())
    
    def _paint_detection(self, frame: np.ndarray, det: Dict) -> None:
        """Paint a single detection onto the frame."""
        # Extract detection properties (handle both Ball and legacy formats)
        x = int(det.get('x', 0))
        y = int(det.get('y', 0))
        radius = int(det.get('r_px', det.get('radius', 10)))
        class_mm = det.get('cls', det.get('class_mm', 0))  # 'cls' in Ball model
        confidence = det.get('conf', det.get('confidence', 1.0))  # 'conf' in Ball model
        
        # Filter by confidence
        if confidence < self._min_confidence:
            return
        
        # Filter by class visibility
        if class_mm in self._visible_classes and not self._visible_classes[class_mm]:
            return
        
        # Get color for class
        color = CLASS_COLORS_BGR.get(class_mm, DEFAULT_COLOR_BGR)
        
        # Draw circle
        cv2.circle(frame, (x, y), radius, color, self._circle_thickness)
        
        # Draw label if enabled
        if self._show_labels:
            label = f"{class_mm}mm"
            label_pos = (x + radius + 5, y)
            cv2.putText(
                frame, label, label_pos,
                cv2.FONT_HERSHEY_SIMPLEX, self._label_font_scale,
                color, 1, cv2.LINE_AA
            )
    
    # ========================================================================
    # Stats
    # ========================================================================
    
    def get_visible_count(self) -> int:
        """Get count of currently visible detections."""
        count = 0
        for det in self._detections:
            class_mm = det.get('cls', det.get('class_mm', 0))
            confidence = det.get('conf', det.get('confidence', 1.0))
            
            if confidence >= self._min_confidence:
                if class_mm not in self._visible_classes or self._visible_classes[class_mm]:
                    count += 1
        
        return count
    
    def get_counts_by_class(self) -> Dict[int, int]:
        """Get detection counts by class (respecting confidence filter)."""
        counts = {4: 0, 6: 0, 8: 0, 10: 0}
        
        for det in self._detections:
            class_mm = det.get('cls', det.get('class_mm', 0))
            confidence = det.get('conf', det.get('confidence', 1.0))
            
            if confidence >= self._min_confidence and class_mm in counts:
                counts[class_mm] += 1
        
        return counts


class OverlayWidget:
    """
    Integrates OverlayPainter with VideoWidget for live overlay rendering.
    
    This is a helper that manages painting overlays from cache data.
    """
    
    def __init__(self, painter: Optional[OverlayPainter] = None):
        self._painter = painter or OverlayPainter()
        self._cache_data: Optional[Dict] = None
        self._frame_lookup: Dict[int, List[Dict]] = {}
    
    def set_cache(self, cache_data: Dict) -> None:
        """
        Load cache data and build frame lookup.
        
        Handles two formats:
        1. Dict format (from ResultsCache):
           {"frames": {"0": {"frame_id": 0, "balls": [...]}, ...}}
        2. List format (legacy):
           {"frames": [{"frame_index": 0, "detections": [...]}, ...]}
        """
        self._cache_data = cache_data
        self._frame_lookup = {}
        
        if not cache_data or 'frames' not in cache_data:
            return
        
        frames = cache_data['frames']
        
        # Handle dict format (keys are string frame IDs)
        if isinstance(frames, dict):
            for fid_str, frame_data in frames.items():
                try:
                    idx = int(fid_str)
                    # Get balls/detections from frame data
                    balls = frame_data.get('balls', [])
                    self._frame_lookup[idx] = balls
                except (ValueError, AttributeError):
                    pass
        # Handle list format
        elif isinstance(frames, list):
            for frame_data in frames:
                idx = frame_data.get('frame_index', frame_data.get('frame_id'))
                if idx is not None:
                    balls = frame_data.get('detections', frame_data.get('balls', []))
                    self._frame_lookup[idx] = balls
    
    def get_painter(self) -> OverlayPainter:
        """Get the underlying painter for configuration."""
        return self._painter
    
    def paint_frame(self, frame_bgr: np.ndarray, frame_index: int) -> np.ndarray:
        """
        Paint overlays for a specific frame.
        
        Args:
            frame_bgr: Frame to paint on (modified in-place)
            frame_index: Frame index to lookup detections for
        
        Returns:
            Frame with overlays
        """
        detections = self._frame_lookup.get(frame_index, [])
        self._painter.set_detections(detections)
        
        # Ensure frame is contiguous (required for OpenCV drawing)
        if not frame_bgr.flags['C_CONTIGUOUS']:
            frame_bgr = np.ascontiguousarray(frame_bgr)
        
        return self._painter.paint(frame_bgr)
    
    def get_stats_for_frame(self, frame_index: int) -> Tuple[int, Dict[int, int]]:
        """Get detection stats for a frame."""
        detections = self._frame_lookup.get(frame_index, [])
        self._painter.set_detections(detections)
        return self._painter.get_visible_count(), self._painter.get_counts_by_class()


# ============================================================================
# Standalone test
# ============================================================================

def main():
    """Test overlay painter with a dummy frame."""
    import sys
    
    # Create test frame
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame[:] = (40, 40, 40)  # Dark gray background
    
    # Draw a fake "drum"
    cv2.circle(frame, (640, 360), 300, (80, 60, 100), -1)
    
    # Create painter
    painter = OverlayPainter()
    
    # Add test detections
    detections = [
        {'x': 500, 'y': 300, 'radius': 15, 'class_mm': 4, 'confidence': 0.9},
        {'x': 600, 'y': 350, 'radius': 20, 'class_mm': 6, 'confidence': 0.85},
        {'x': 700, 'y': 400, 'radius': 25, 'class_mm': 8, 'confidence': 0.75},
        {'x': 550, 'y': 420, 'radius': 30, 'class_mm': 10, 'confidence': 0.6},
        {'x': 650, 'y': 280, 'radius': 18, 'class_mm': 6, 'confidence': 0.4},  # Below threshold
    ]
    
    painter.set_detections(detections)
    painter.set_show_labels(True)
    
    # Paint
    result = painter.paint(frame)
    
    # Show stats
    print(f"Visible: {painter.get_visible_count()}")
    print(f"By class: {painter.get_counts_by_class()}")
    
    # Display
    cv2.imshow("Overlay Test", result)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
