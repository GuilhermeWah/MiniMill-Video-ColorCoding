# MillPresenter — Video Widget (STEP-11)

"""
Video viewport widget with zoom and pan support.

Features:
- Displays video frames from FrameLoader
- Zoom: Fit, 100%, +/- with mouse wheel
- Pan: Click and drag when zoomed
- Efficient QPixmap caching
- Maintains aspect ratio
- Qt-based overlay rendering (fast!)
"""

from typing import Optional, Tuple, List, Dict
import numpy as np

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal, Slot, QPoint, QPointF, QRectF, QSize
from PySide6.QtGui import QImage, QPixmap, QPainter, QMouseEvent, QWheelEvent, QPen, QColor


class VideoWidget(QWidget):
    """
    Video viewport with zoom and pan.
    
    Signals:
        frame_clicked(x, y): Emitted when frame is clicked (video coordinates)
        zoom_changed(float): Emitted when zoom level changes
    """
    
    frame_clicked = Signal(int, int)  # x, y in video coordinates
    zoom_changed = Signal(float)      # zoom factor
    
    # Zoom levels
    ZOOM_MIN = 0.1
    ZOOM_MAX = 5.0
    ZOOM_STEP = 0.1
    
    # Pre-allocated pen colors for overlay classes (RGB)
    CLASS_COLORS = {
        4: QColor(158, 206, 106),   # Green - 4mm
        6: QColor(122, 162, 247),   # Blue - 6mm  
        8: QColor(224, 175, 104),   # Orange - 8mm
        10: QColor(247, 118, 142),  # Pink - 10mm
    }
    DEFAULT_COLOR = QColor(200, 200, 200)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        # Frame state
        self._pixmap: Optional[QPixmap] = None
        self._frame_size = QSize(0, 0)  # Original frame dimensions
        
        # Zoom/pan state
        self._zoom = 1.0
        self._fit_mode = True  # If True, auto-fit to widget
        self._pan_offset = QPointF(0, 0)  # Pan offset in widget coordinates
        
        # Drag state
        self._dragging = False
        self._drag_start = QPoint(0, 0)
        self._pan_start = QPointF(0, 0)
        
        # Overlay state (detections to draw)
        self._overlays: List[Dict] = []
        self._visible_classes: Dict[int, bool] = {4: True, 6: True, 8: True, 10: True}
        self._min_confidence: float = 0.5
        
        # Pre-allocate pens for each class
        self._pens: Dict[int, QPen] = {}
        for cls, color in self.CLASS_COLORS.items():
            pen = QPen(color)
            pen.setWidth(2)
            self._pens[cls] = pen
        self._default_pen = QPen(self.DEFAULT_COLOR)
        self._default_pen.setWidth(2)
        
        # Calibration overlay points
        self._calibration_points: List[Tuple[int, int]] = []
        
        # Widget setup
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Background color (matches app theme)
        self.setStyleSheet("background-color: #08080c;")
    
    # ========================================================================
    # Frame display
    # ========================================================================
    
    def set_frame(self, frame_bgr: np.ndarray) -> None:
        """
        Display a BGR frame (from OpenCV/FrameLoader).
        
        Args:
            frame_bgr: numpy array with shape (H, W, 3) in BGR format
        """
        h, w = frame_bgr.shape[:2]
        self._frame_size = QSize(w, h)
        
        # Convert BGR to RGB
        frame_rgb = frame_bgr[:, :, ::-1].copy()
        
        # Create QImage (no copy, shares data)
        bytes_per_line = 3 * w
        qimage = QImage(
            frame_rgb.data, w, h, bytes_per_line,
            QImage.Format_RGB888
        )
        
        # Convert to QPixmap for efficient rendering
        self._pixmap = QPixmap.fromImage(qimage)
        
        # Update zoom if in fit mode
        if self._fit_mode:
            self._calculate_fit_zoom()
        
        self.update()
    
    def clear(self) -> None:
        """Clear the displayed frame."""
        self._pixmap = None
        self._frame_size = QSize(0, 0)
        self.update()
    
    def has_frame(self) -> bool:
        """Check if a frame is currently displayed."""
        return self._pixmap is not None
    
    # ========================================================================
    # Overlay control
    # ========================================================================
    
    def set_overlays(self, detections: List[Dict]) -> None:
        """
        Set detections to draw as overlays.
        
        Each detection should have: x, y, r_px (or radius), cls (or class_mm), conf (or confidence)
        """
        self._overlays = detections or []
        self.update()
    
    def clear_overlays(self) -> None:
        """Clear overlay detections."""
        self._overlays = []
        self.update()
    
    def set_class_visible(self, class_mm: int, visible: bool) -> None:
        """Set visibility for a size class."""
        if class_mm in self._visible_classes:
            self._visible_classes[class_mm] = visible
            self.update()
    
    def set_min_confidence(self, confidence: float) -> None:
        """Set minimum confidence threshold for overlay display."""
        self._min_confidence = max(0.0, min(1.0, confidence))
        self.update()
    
    def set_calibration_points(self, points: List[Tuple[int, int]]) -> None:
        """Set calibration points to draw."""
        self._calibration_points = points or []
        self.update()
    
    # ========================================================================
    # Zoom control
    # ========================================================================
    
    def set_zoom(self, zoom: float) -> None:
        """Set absolute zoom level."""
        self._fit_mode = False
        self._zoom = max(self.ZOOM_MIN, min(self.ZOOM_MAX, zoom))
        self._clamp_pan()
        self.zoom_changed.emit(self._zoom)
        self.update()
    
    def zoom_in(self) -> None:
        """Zoom in by one step."""
        self.set_zoom(self._zoom + self.ZOOM_STEP)
    
    def zoom_out(self) -> None:
        """Zoom out by one step."""
        self.set_zoom(self._zoom - self.ZOOM_STEP)
    
    def zoom_fit(self) -> None:
        """Fit frame to widget size."""
        self._fit_mode = True
        self._pan_offset = QPointF(0, 0)
        self._calculate_fit_zoom()
        self.zoom_changed.emit(self._zoom)
        self.update()
    
    def zoom_100(self) -> None:
        """Set zoom to 100% (actual pixels)."""
        self._fit_mode = False
        self._zoom = 1.0
        self._pan_offset = QPointF(0, 0)
        self.zoom_changed.emit(self._zoom)
        self.update()
    
    def get_zoom(self) -> float:
        """Get current zoom level."""
        return self._zoom
    
    def is_fit_mode(self) -> bool:
        """Check if in fit mode."""
        return self._fit_mode
    
    def _calculate_fit_zoom(self) -> None:
        """Calculate zoom to fit frame in widget."""
        if self._frame_size.isEmpty():
            self._zoom = 1.0
            return
        
        widget_w = self.width()
        widget_h = self.height()
        frame_w = self._frame_size.width()
        frame_h = self._frame_size.height()
        
        if frame_w <= 0 or frame_h <= 0:
            self._zoom = 1.0
            return
        
        # Calculate zoom to fit while maintaining aspect ratio
        zoom_x = widget_w / frame_w
        zoom_y = widget_h / frame_h
        self._zoom = min(zoom_x, zoom_y)
    
    # ========================================================================
    # Pan control
    # ========================================================================
    
    def _clamp_pan(self) -> None:
        """Clamp pan offset to keep frame in view."""
        if self._frame_size.isEmpty():
            self._pan_offset = QPointF(0, 0)
            return
        
        # Calculate scaled frame size
        scaled_w = self._frame_size.width() * self._zoom
        scaled_h = self._frame_size.height() * self._zoom
        
        # Calculate max pan (how much frame can move)
        max_pan_x = max(0, (scaled_w - self.width()) / 2)
        max_pan_y = max(0, (scaled_h - self.height()) / 2)
        
        # Clamp
        x = max(-max_pan_x, min(max_pan_x, self._pan_offset.x()))
        y = max(-max_pan_y, min(max_pan_y, self._pan_offset.y()))
        self._pan_offset = QPointF(x, y)
    
    # ========================================================================
    # Coordinate conversion
    # ========================================================================
    
    def widget_to_frame(self, widget_pos: QPoint) -> Tuple[int, int]:
        """
        Convert widget coordinates to frame coordinates.
        
        Returns:
            (x, y) in original frame pixel space, or (-1, -1) if outside frame
        """
        if self._frame_size.isEmpty():
            return (-1, -1)
        
        # Get frame rect in widget space
        rect = self._get_frame_rect()
        
        # Check if inside frame
        if not rect.contains(widget_pos.toPointF()):
            return (-1, -1)
        
        # Calculate position relative to frame rect
        rel_x = widget_pos.x() - rect.x()
        rel_y = widget_pos.y() - rect.y()
        
        # Scale to frame coordinates
        frame_x = int(rel_x / self._zoom)
        frame_y = int(rel_y / self._zoom)
        
        # Clamp to frame bounds
        frame_x = max(0, min(self._frame_size.width() - 1, frame_x))
        frame_y = max(0, min(self._frame_size.height() - 1, frame_y))
        
        return (frame_x, frame_y)
    
    def _get_frame_rect(self) -> QRectF:
        """Get the frame rectangle in widget coordinates."""
        if self._frame_size.isEmpty():
            return QRectF()
        
        # Scaled size
        scaled_w = self._frame_size.width() * self._zoom
        scaled_h = self._frame_size.height() * self._zoom
        
        # Centered position with pan offset
        x = (self.width() - scaled_w) / 2 + self._pan_offset.x()
        y = (self.height() - scaled_h) / 2 + self._pan_offset.y()
        
        return QRectF(x, y, scaled_w, scaled_h)
    
    # ========================================================================
    # Qt event handlers
    # ========================================================================
    
    def paintEvent(self, event) -> None:
        """Paint the video frame and overlays."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), Qt.black)
        
        if self._pixmap is None:
            return
        
        # Get frame destination rect
        rect = self._get_frame_rect()
        
        # Draw the frame
        painter.drawPixmap(rect.toRect(), self._pixmap)
        
        # Draw overlays (detection circles)
        if self._overlays:
            self._draw_overlays(painter, rect)
        
        # Draw calibration markers
        if self._calibration_points:
            self._draw_calibration_overlay(painter, rect)
    
    def _draw_calibration_overlay(self, painter: QPainter, frame_rect: QRectF) -> None:
        """Draw calibration point markers and line."""
        # Yellow pen for calibration
        pen = QPen(QColor(255, 255, 0))
        pen.setWidth(3)
        painter.setPen(pen)
        
        screen_points = []
        for px, py in self._calibration_points:
            # Convert to screen coordinates
            sx = frame_rect.x() + px * self._zoom
            sy = frame_rect.y() + py * self._zoom
            screen_points.append((sx, sy))
            
            # Draw crosshair marker
            size = 15
            painter.drawLine(int(sx - size), int(sy), int(sx + size), int(sy))
            painter.drawLine(int(sx), int(sy - size), int(sx), int(sy + size))
            
            # Draw circle around point
            painter.drawEllipse(QPointF(sx, sy), size, size)
        
        # Draw line between points if two exist
        if len(screen_points) == 2:
            p1, p2 = screen_points
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))
    
    def _draw_overlays(self, painter: QPainter, frame_rect: QRectF) -> None:
        """Draw detection circles in screen space."""
        for det in self._overlays:
            # Extract detection properties
            x = det.get('x', 0)
            y = det.get('y', 0)
            radius = det.get('r_px', det.get('radius', 10))
            cls = det.get('cls', det.get('class_mm', 0))
            conf = det.get('conf', det.get('confidence', 1.0))
            
            # Filter by confidence
            if conf < self._min_confidence:
                continue
            
            # Filter by class visibility
            if cls in self._visible_classes and not self._visible_classes[cls]:
                continue
            
            # Convert frame coordinates to screen coordinates
            screen_x = frame_rect.x() + x * self._zoom
            screen_y = frame_rect.y() + y * self._zoom
            screen_r = radius * self._zoom
            
            # Get pen for class
            pen = self._pens.get(cls, self._default_pen)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            
            # Draw circle
            painter.drawEllipse(QPointF(screen_x, screen_y), screen_r, screen_r)
    def resizeEvent(self, event) -> None:
        """Handle widget resize."""
        super().resizeEvent(event)
        
        if self._fit_mode:
            self._calculate_fit_zoom()
        else:
            self._clamp_pan()
        
        self.update()
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press for pan and click."""
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_start = event.pos()
            self._pan_start = self._pan_offset
            self.setCursor(Qt.ClosedHandCursor)
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move for pan."""
        if self._dragging:
            delta = event.pos() - self._drag_start
            self._pan_offset = self._pan_start + QPointF(delta.x(), delta.y())
            self._clamp_pan()
            self.update()
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release."""
        if event.button() == Qt.LeftButton:
            if self._dragging:
                # Check if it was a click (minimal movement)
                delta = event.pos() - self._drag_start
                if abs(delta.x()) < 5 and abs(delta.y()) < 5:
                    # It was a click
                    frame_x, frame_y = self.widget_to_frame(event.pos())
                    if frame_x >= 0 and frame_y >= 0:
                        print(f"[VIDEO_WIDGET] Click detected at frame ({frame_x}, {frame_y})")
                        self.frame_clicked.emit(frame_x, frame_y)
            
            self._dragging = False
            self.setCursor(Qt.ArrowCursor)
        
        super().mouseReleaseEvent(event)
    
    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle mouse wheel for zoom."""
        if self._pixmap is None:
            return
        
        # Calculate zoom delta
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_in()
        elif delta < 0:
            self.zoom_out()
        
        event.accept()
    
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Handle double-click to toggle fit/100%."""
        if event.button() == Qt.LeftButton:
            if self._fit_mode:
                self.zoom_100()
            else:
                self.zoom_fit()
        
        super().mouseDoubleClickEvent(event)


# ============================================================================
# Standalone test
# ============================================================================

def main():
    """Test the video widget with a dummy frame."""
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
    
    app = QApplication(sys.argv)
    
    # Create test window
    window = QMainWindow()
    window.setWindowTitle("VideoWidget Test")
    window.resize(800, 600)
    
    central = QWidget()
    window.setCentralWidget(central)
    layout = QVBoxLayout(central)
    
    # Video widget
    video = VideoWidget()
    layout.addWidget(video, 1)
    
    # Controls
    controls = QHBoxLayout()
    
    btn_fit = QPushButton("Fit")
    btn_fit.clicked.connect(video.zoom_fit)
    controls.addWidget(btn_fit)
    
    btn_100 = QPushButton("100%")
    btn_100.clicked.connect(video.zoom_100)
    controls.addWidget(btn_100)
    
    btn_in = QPushButton("+")
    btn_in.clicked.connect(video.zoom_in)
    controls.addWidget(btn_in)
    
    btn_out = QPushButton("−")
    btn_out.clicked.connect(video.zoom_out)
    controls.addWidget(btn_out)
    
    layout.addLayout(controls)
    
    # Create a test frame (gradient)
    test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    for y in range(720):
        for x in range(1280):
            test_frame[y, x] = [x % 256, y % 256, (x + y) % 256]
    
    # Add some shapes
    import cv2
    cv2.circle(test_frame, (640, 360), 200, (0, 255, 0), 3)
    cv2.rectangle(test_frame, (100, 100), (300, 300), (255, 0, 0), 2)
    cv2.putText(test_frame, "VideoWidget Test", (400, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
    
    video.set_frame(test_frame)
    
    # Show zoom level
    def on_zoom(z):
        window.setWindowTitle(f"VideoWidget Test — Zoom: {z:.1%}")
    video.zoom_changed.connect(on_zoom)
    
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
