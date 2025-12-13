"""
Video Viewport Widget

Central canvas for displaying video frames with detection overlays.

Features:
- Hardware-accelerated rendering (optional OpenGL)
- Zoom and pan interaction
- Overlay rendering from cached detections
- Aspect ratio preservation (letterboxing)

HCI Principles Applied:
- Direct Manipulation: Zoom with wheel, pan with drag
- Feedback: Cursor changes indicate available actions
- Undo-friendly: Double-click resets view
"""

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal, Slot, QPoint, QRect, QSize
from PySide6.QtGui import (
    QPainter, QImage, QPixmap, QColor, QPen, QBrush,
    QMouseEvent, QWheelEvent, QResizeEvent, QTransform
)

import numpy as np
from typing import Optional, List, Tuple

from ui.theme import COLORS, CLASS_COLORS


class VideoViewport(QWidget):
    """
    Video frame display widget with overlay support.
    
    Displays video frames and renders detection overlays.
    Supports zoom and pan for detailed inspection.
    
    Signals:
        frame_clicked: Emitted when user clicks on viewport (x, y in frame coords)
        detection_hovered: Emitted when mouse hovers over a detection
        zoom_changed: Emitted when zoom level changes
        two_point_measured: Emitted when two points measured (pixel_distance)
        roi_drag_finished: Emitted when ROI drag ends (cx, cy, radius)
    """
    
    frame_clicked = Signal(int, int)  # Frame coordinates
    detection_hovered = Signal(dict)  # Detection info or empty dict
    zoom_changed = Signal(float)
    two_point_measured = Signal(float)  # Pixel distance between two points
    roi_drag_finished = Signal(int, int, int)  # center_x, center_y, radius
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Frame data
        self._frame: Optional[QImage] = None
        self._frame_size = QSize(0, 0)
        
        # Overlay data
        self._detections: List[dict] = []
        self._preview_detections: List[dict] = []  # Temporary preview detections
        self._show_overlays = True
        self._overlay_opacity = 1.0
        self._visible_classes = set(CLASS_COLORS.all_classes())
        self._min_confidence = 0.0
        self._show_size_labels = False
        self._show_conf_labels = False
        
        # Drum ROI (optional visualization)
        self._show_roi = False
        self._drum_center: Optional[Tuple[int, int]] = None
        self._drum_radius: int = 0
        
        # View transform (zoom/pan)
        self._zoom = 1.0
        self._pan_offset = QPoint(0, 0)
        self._min_zoom = 0.1
        self._max_zoom = 10.0
        
        # Interaction state
        self._is_panning = False
        self._pan_start = QPoint()
        self._last_mouse_pos = QPoint()
        
        # Two-point measurement mode
        self._two_point_mode = False
        self._two_point_start: Optional[Tuple[int, int]] = None
        self._two_point_end: Optional[Tuple[int, int]] = None
        
        # ROI adjustment mode
        self._roi_adjust_mode = False
        self._roi_dragging = False
        self._roi_drag_type: Optional[str] = None  # "center" or "edge"
        self._roi_drag_start: Optional[Tuple[int, int]] = None
        self._roi_original_center: Optional[Tuple[int, int]] = None
        self._roi_original_radius: int = 0
        
        # Setup
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Background color
        self.setStyleSheet(f"background-color: {COLORS.BG_DARK};")
    
    # =========================================================================
    # Public API
    # =========================================================================
    
    def set_frame(self, frame: np.ndarray):
        """
        Set the current video frame to display.
        
        Args:
            frame: BGR numpy array from OpenCV
        """
        if frame is None:
            self._frame = None
            self._frame_size = QSize(0, 0)
            self.update()
            return
        
        h, w = frame.shape[:2]
        
        # Convert BGR to RGB efficiently using cv2
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            # Use cv2.cvtColor which is optimized (faster than numpy slicing)
            import cv2
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            rgb = frame
        
        bytes_per_line = 3 * w
        
        # Create QImage - need to copy since numpy array will be reused
        self._frame = QImage(
            rgb.data, w, h, bytes_per_line, 
            QImage.Format.Format_RGB888
        ).copy()
        
        self._frame_size = QSize(w, h)
        self.update()
    
    def set_frame_qimage(self, image: QImage):
        """Set frame directly from QImage."""
        self._frame = image
        self._frame_size = image.size() if image else QSize(0, 0)
        self.update()
    
    def set_detections(self, detections: List[dict]):
        """
        Set detection overlays to draw (from cache).
        
        Args:
            detections: List of detection dicts with keys:
                - x, y: center coordinates (pixels)
                - r_px: radius (pixels)
                - conf: confidence (0.0-1.0)
                - cls: class name ("4mm", "6mm", etc.)
        """
        self._detections = detections or []
        # Don't clear preview detections here - let them persist
        # Preview is cleared when frame changes or explicitly cleared
        self.update()
    
    def set_preview_detections(self, detections: List[dict]):
        """
        Set preview detection overlays (temporary, for tuning).
        
        Preview detections are drawn with a distinct style (dashed circles)
        and replace normal detections until cleared.
        
        Args:
            detections: List of detection dicts
        """
        self._preview_detections = detections or []
        self.update()
    
    def clear_preview_detections(self):
        """Clear preview detections, showing cached detections again."""
        self._preview_detections = []
        self.update()
    
    def set_overlay_visibility(self, show: bool):
        """Show or hide all overlays."""
        self._show_overlays = show
        self.update()
    
    def set_overlay_opacity(self, opacity: float):
        """Set overlay opacity (0.0 - 1.0)."""
        self._overlay_opacity = max(0.0, min(1.0, opacity))
        self.update()
    
    def set_visible_classes(self, classes: set):
        """Set which classes to show."""
        self._visible_classes = classes
        self.update()
    
    def set_min_confidence(self, threshold: float):
        """Set minimum confidence threshold for display."""
        self._min_confidence = threshold
        self.update()
    
    def set_label_options(self, show_size: bool, show_conf: bool):
        """Set label visibility options."""
        self._show_size_labels = show_size
        self._show_conf_labels = show_conf
        self.update()
    
    def set_drum_roi(self, center: Tuple[int, int], radius: int, show: bool = True):
        """Set drum ROI for visualization."""
        self._drum_center = center
        self._drum_radius = radius
        self._show_roi = show
        self.update()
    
    def show_roi(self, show: bool):
        """Toggle ROI visibility."""
        self._show_roi = show
        self.update()
    
    def set_two_point_mode(self, enabled: bool):
        """Enable or disable two-point measurement mode."""
        self._two_point_mode = enabled
        if not enabled:
            self._two_point_start = None
            self._two_point_end = None
        self.update()
        if enabled:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def adjust_roi(self, dx: int, dy: int, dr: int):
        """Adjust ROI center and radius by delta values."""
        if self._drum_center:
            new_cx = self._drum_center[0] + dx
            new_cy = self._drum_center[1] + dy
            new_r = max(50, self._drum_radius + dr)
            self._drum_center = (new_cx, new_cy)
            self._drum_radius = new_r
            self.roi_drag_finished.emit(new_cx, new_cy, new_r)
            self.update()
    
    def reset_view(self):
        """Reset zoom and pan to default."""
        self._zoom = 1.0
        self._pan_offset = QPoint(0, 0)
        self.zoom_changed.emit(self._zoom)
        self.update()
    
    def zoom_in(self):
        """Zoom in by a step."""
        self._set_zoom(self._zoom * 1.25)
    
    def zoom_out(self):
        """Zoom out by a step."""
        self._set_zoom(self._zoom / 1.25)
    
    def get_zoom(self) -> float:
        """Get current zoom level."""
        return self._zoom
    
    # =========================================================================
    # Painting
    # =========================================================================
    
    def paintEvent(self, event):
        """Draw the frame and overlays."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Fill background
        painter.fillRect(self.rect(), QColor(COLORS.BG_DARK))
        
        if self._frame is None:
            # Draw placeholder text
            painter.setPen(QColor(COLORS.TEXT_SECONDARY))
            painter.drawText(
                self.rect(), 
                Qt.AlignmentFlag.AlignCenter,
                "No video loaded"
            )
            return
        
        # Calculate display rect (centered, aspect-preserving)
        display_rect = self._get_display_rect()
        
        # Apply zoom and pan transform
        transform = QTransform()
        center = display_rect.center()
        transform.translate(center.x(), center.y())
        transform.scale(self._zoom, self._zoom)
        transform.translate(-center.x() + self._pan_offset.x(), 
                          -center.y() + self._pan_offset.y())
        
        painter.setTransform(transform)
        
        # Draw frame
        painter.drawImage(display_rect, self._frame)
        
        # Draw ROI if enabled
        if self._show_roi and self._drum_center and self._drum_radius > 0:
            self._draw_roi(painter, display_rect)
        
        # Draw overlays (preview detections take priority)
        if self._show_overlays:
            if self._preview_detections:
                self._draw_overlays(painter, display_rect, self._preview_detections, is_preview=True)
            elif self._detections:
                self._draw_overlays(painter, display_rect, self._detections, is_preview=False)
        
        # Draw two-point measurement line
        if self._two_point_mode and self._two_point_start:
            self._draw_measurement_line(painter, display_rect)
        
        painter.end()
    
    def _get_display_rect(self) -> QRect:
        """Calculate the display rectangle maintaining aspect ratio."""
        if self._frame_size.isEmpty():
            return QRect()
        
        widget_size = self.size()
        frame_aspect = self._frame_size.width() / self._frame_size.height()
        widget_aspect = widget_size.width() / widget_size.height()
        
        if frame_aspect > widget_aspect:
            # Frame is wider - fit to width
            display_width = widget_size.width()
            display_height = int(display_width / frame_aspect)
        else:
            # Frame is taller - fit to height
            display_height = widget_size.height()
            display_width = int(display_height * frame_aspect)
        
        x = (widget_size.width() - display_width) // 2
        y = (widget_size.height() - display_height) // 2
        
        return QRect(x, y, display_width, display_height)
    
    def _draw_roi(self, painter: QPainter, display_rect: QRect):
        """Draw drum ROI circle in RED for visibility."""
        # Scale frame coords to display coords
        scale_x = display_rect.width() / self._frame_size.width()
        scale_y = display_rect.height() / self._frame_size.height()
        
        cx = display_rect.x() + int(self._drum_center[0] * scale_x)
        cy = display_rect.y() + int(self._drum_center[1] * scale_y)
        r = int(self._drum_radius * scale_x)
        
        # Red color for high visibility
        pen = QPen(QColor(255, 0, 0, 200))  # RED with alpha
        pen.setWidth(3)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPoint(cx, cy), r, r)
        
        # Draw center marker
        painter.setPen(QPen(QColor(255, 0, 0, 200), 2))
        painter.drawLine(cx - 10, cy, cx + 10, cy)
        painter.drawLine(cx, cy - 10, cx, cy + 10)
    
    def _draw_measurement_line(self, painter: QPainter, display_rect: QRect):
        """Draw two-point measurement visualization."""
        if self._frame_size.isEmpty() or not self._two_point_start:
            return
        
        # Scale frame coords to display coords
        scale_x = display_rect.width() / self._frame_size.width()
        scale_y = display_rect.height() / self._frame_size.height()
        
        # First point - minimal crosshair only (no filled circle)
        x1 = display_rect.x() + int(self._two_point_start[0] * scale_x)
        y1 = display_rect.y() + int(self._two_point_start[1] * scale_y)
        
        # Draw first point - thin crosshair only for minimal visual footprint
        painter.setPen(QPen(QColor(0, 255, 0, 255), 1))
        painter.setBrush(Qt.NoBrush)
        # Short crosshair lines (5px each direction)
        painter.drawLine(x1 - 5, y1, x1 + 5, y1)
        painter.drawLine(x1, y1 - 5, x1, y1 + 5)
        
        # If second point exists, draw line
        if self._two_point_end:
            x2 = display_rect.x() + int(self._two_point_end[0] * scale_x)
            y2 = display_rect.y() + int(self._two_point_end[1] * scale_y)
            
            # Draw line (yellow, thin)
            pen = QPen(QColor(255, 255, 0, 255))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(x1, y1, x2, y2)
            
            # Draw second point - thin crosshair only
            painter.setPen(QPen(QColor(0, 255, 0, 255), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawLine(x2 - 5, y2, x2 + 5, y2)
            painter.drawLine(x2, y2 - 5, x2, y2 + 5)
            
            # Calculate and display pixel distance
            dx = self._two_point_end[0] - self._two_point_start[0]
            dy = self._two_point_end[1] - self._two_point_start[1]
            pixel_dist = (dx**2 + dy**2) ** 0.5
            
            # Draw distance label
            mid_x = (x1 + x2) // 2
            mid_y = (y1 + y2) // 2 - 10
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(mid_x - 30, mid_y, f"{pixel_dist:.1f} px")
    
    def _draw_overlays(self, painter: QPainter, display_rect: QRect, 
                        detections: List[dict] = None, is_preview: bool = False):
        """Draw detection circles.
        
        Args:
            painter: QPainter instance
            display_rect: Display area rectangle
            detections: List of detections to draw (defaults to self._detections)
            is_preview: If True, draw with preview styling (thinner lines, no labels)
        """
        if self._frame_size.isEmpty():
            return
        
        if detections is None:
            detections = self._detections
        
        # Scale factor
        scale_x = display_rect.width() / self._frame_size.width()
        scale_y = display_rect.height() / self._frame_size.height()
        
        for det in detections:
            # Filter by class and confidence (skip for preview)
            cls = det.get("cls", "unknown")
            conf = det.get("conf", 0.0)
            
            if not is_preview:
                if cls not in self._visible_classes:
                    continue
                if conf < self._min_confidence:
                    continue
            
            # Get coordinates
            x = det.get("x", 0)
            y = det.get("y", 0)
            r = det.get("r_px", 10)
            
            # Transform to display coordinates
            dx = display_rect.x() + int(x * scale_x)
            dy = display_rect.y() + int(y * scale_y)
            dr = int(r * scale_x)
            
            # Get color - preview uses cyan for visibility
            if is_preview:
                color = QColor("#00FFFF")  # Cyan for preview
                color.setAlphaF(0.9)
            else:
                color_hex = CLASS_COLORS.get_hex(cls)
                color = QColor(color_hex)
                color.setAlphaF(self._overlay_opacity)
            
            # Draw circle - thinner for preview (cleaner look)
            pen = QPen(color)
            pen.setWidth(1 if is_preview else 2)
            if is_preview:
                pen.setStyle(Qt.PenStyle.DashLine)  # Dashed for preview
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPoint(dx, dy), dr, dr)
            
            # Draw center dot - smaller for preview
            painter.setBrush(QBrush(color))
            center_size = 1 if is_preview else 2
            painter.drawEllipse(QPoint(dx, dy), center_size, center_size)
            
            # Draw labels only for playback mode, NOT for preview
            if not is_preview and (self._show_size_labels or self._show_conf_labels):
                self._draw_label(painter, dx, dy, dr, cls, conf, is_preview)
    
    def _draw_label(self, painter: QPainter, x: int, y: int, r: int, 
                    cls: str, conf: float, is_preview: bool = False):
        """Draw text label for a detection."""
        parts = []
        
        if self._show_size_labels:
            parts.append(cls)
        if self._show_conf_labels:
            parts.append(f"{conf:.2f}")
        
        if not parts:
            return
        
        text = " ".join(parts)
        
        painter.setPen(QColor(COLORS.TEXT_PRIMARY))
        painter.drawText(x + r + 4, y + 4, text)
    
    # =========================================================================
    # Mouse Interaction
    # =========================================================================
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for panning or two-point measurement."""
        # Right-click to reset two-point measurement
        if event.button() == Qt.MouseButton.RightButton:
            if self._two_point_mode:
                self._two_point_start = None
                self._two_point_end = None
                self.update()
                return
        
        if event.button() == Qt.MouseButton.LeftButton:
            # Two-point measurement mode
            if self._two_point_mode and self._frame is not None:
                frame_coords = self._widget_to_frame_coords(event.pos())
                if frame_coords:
                    if self._two_point_start is None:
                        # First click - set first point
                        self._two_point_start = frame_coords
                        self._two_point_end = None
                        self.update()
                    elif self._two_point_end is None:
                        # Second click - set second point
                        self._two_point_end = frame_coords
                        # Calculate pixel distance
                        dx = self._two_point_end[0] - self._two_point_start[0]
                        dy = self._two_point_end[1] - self._two_point_start[1]
                        pixel_dist = (dx**2 + dy**2) ** 0.5
                        self.two_point_measured.emit(pixel_dist)
                        self.update()
                    else:
                        # Third click - replace first point with new one (cycle)
                        self._two_point_start = self._two_point_end
                        self._two_point_end = frame_coords
                        # Calculate new pixel distance
                        dx = self._two_point_end[0] - self._two_point_start[0]
                        dy = self._two_point_end[1] - self._two_point_start[1]
                        pixel_dist = (dx**2 + dy**2) ** 0.5
                        self.two_point_measured.emit(pixel_dist)
                        self.update()
                return
            
            # ROI dragging when ROI is visible
            if self._show_roi and self._drum_center and self._frame is not None:
                frame_coords = self._widget_to_frame_coords(event.pos())
                if frame_coords:
                    # Check if click is near center or edge of ROI
                    dx = frame_coords[0] - self._drum_center[0]
                    dy = frame_coords[1] - self._drum_center[1]
                    dist_from_center = (dx**2 + dy**2) ** 0.5
                    
                    # Near center (within 20% of radius) = move
                    # Near edge (within 15px of radius) = resize
                    center_threshold = self._drum_radius * 0.2
                    edge_threshold = 20  # pixels tolerance for edge
                    
                    if dist_from_center < center_threshold:
                        self._roi_dragging = True
                        self._roi_drag_type = "center"
                        self._roi_drag_start = frame_coords
                        self._roi_original_center = self._drum_center
                        self._roi_original_radius = self._drum_radius
                        self.setCursor(Qt.CursorShape.SizeAllCursor)
                        return
                    elif abs(dist_from_center - self._drum_radius) < edge_threshold:
                        self._roi_dragging = True
                        self._roi_drag_type = "edge"
                        self._roi_drag_start = frame_coords
                        self._roi_original_center = self._drum_center
                        self._roi_original_radius = self._drum_radius
                        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                        return
            
            # Regular panning when zoomed
            if self._zoom > 1.0:
                self._is_panning = True
                self._pan_start = event.pos()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
        
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._roi_dragging:
                # Finish ROI drag
                self._roi_dragging = False
                self._roi_drag_type = None
                self.roi_drag_finished.emit(
                    self._drum_center[0], 
                    self._drum_center[1], 
                    self._drum_radius
                )
                self.setCursor(Qt.CursorShape.ArrowCursor)
            elif self._is_panning:
                self._is_panning = False
                self.setCursor(Qt.CursorShape.ArrowCursor)
            elif self._frame is not None and not self._two_point_mode:
                # Click without drag - emit frame coordinates
                frame_coords = self._widget_to_frame_coords(event.pos())
                if frame_coords:
                    self.frame_clicked.emit(frame_coords[0], frame_coords[1])
        
        super().mouseReleaseEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for panning, ROI dragging, and hover detection."""
        if self._roi_dragging and self._frame is not None:
            frame_coords = self._widget_to_frame_coords(event.pos())
            if frame_coords and self._roi_original_center:
                if self._roi_drag_type == "center":
                    # Move entire circle
                    dx = frame_coords[0] - self._roi_drag_start[0]
                    dy = frame_coords[1] - self._roi_drag_start[1]
                    new_cx = self._roi_original_center[0] + dx
                    new_cy = self._roi_original_center[1] + dy
                    self._drum_center = (new_cx, new_cy)
                    self.update()
                elif self._roi_drag_type == "edge":
                    # Resize circle - calculate new radius from distance to center
                    dx = frame_coords[0] - self._drum_center[0]
                    dy = frame_coords[1] - self._drum_center[1]
                    new_radius = int((dx**2 + dy**2) ** 0.5)
                    self._drum_radius = max(50, new_radius)
                    self.update()
        elif self._is_panning:
            delta = event.pos() - self._pan_start
            self._pan_offset += delta
            self._pan_start = event.pos()
            self.update()
        else:
            # Check for detection hover
            self._check_detection_hover(event.pos())
            
            # Update cursor based on ROI proximity or zoom level
            if self._show_roi and self._drum_center and self._frame is not None:
                frame_coords = self._widget_to_frame_coords(event.pos())
                if frame_coords:
                    dx = frame_coords[0] - self._drum_center[0]
                    dy = frame_coords[1] - self._drum_center[1]
                    dist_from_center = (dx**2 + dy**2) ** 0.5
                    center_threshold = self._drum_radius * 0.2
                    edge_threshold = 20
                    
                    if dist_from_center < center_threshold:
                        self.setCursor(Qt.CursorShape.SizeAllCursor)
                    elif abs(dist_from_center - self._drum_radius) < edge_threshold:
                        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                    elif self._two_point_mode:
                        self.setCursor(Qt.CursorShape.CrossCursor)
                    elif self._zoom > 1.0:
                        self.setCursor(Qt.CursorShape.OpenHandCursor)
                    else:
                        self.setCursor(Qt.CursorShape.ArrowCursor)
            elif self._two_point_mode:
                self.setCursor(Qt.CursorShape.CrossCursor)
            elif self._zoom > 1.0:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        
        self._last_mouse_pos = event.pos()
        super().mouseMoveEvent(event)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Reset view on double-click."""
        self.reset_view()
        super().mouseDoubleClickEvent(event)
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle zoom with mouse wheel."""
        delta = event.angleDelta().y()
        
        if delta > 0:
            factor = 1.1
        else:
            factor = 0.9
        
        # Zoom centered on mouse position
        old_zoom = self._zoom
        self._set_zoom(self._zoom * factor)
        
        if self._zoom != old_zoom:
            # Adjust pan to zoom toward mouse position
            mouse_pos = event.position().toPoint()
            center = self.rect().center()
            diff = mouse_pos - center
            # Calculate new offset (arithmetic with QPoint stays as QPoint)
            new_offset = self._pan_offset - QPoint(
                int(diff.x() * (1 - factor)),
                int(diff.y() * (1 - factor))
            )
            self._pan_offset = new_offset
        
        event.accept()
    
    def _set_zoom(self, zoom: float):
        """Set zoom level with clamping."""
        new_zoom = max(self._min_zoom, min(self._max_zoom, zoom))
        if new_zoom != self._zoom:
            self._zoom = new_zoom
            self.zoom_changed.emit(self._zoom)
            self.update()
    
    def _widget_to_frame_coords(self, widget_pos: QPoint) -> Optional[Tuple[int, int]]:
        """Convert widget coordinates to frame coordinates."""
        if self._frame is None or self._frame_size.isEmpty():
            return None
        
        display_rect = self._get_display_rect()
        
        # Apply inverse transform
        center = display_rect.center()
        
        # Remove zoom and pan
        x = (widget_pos.x() - center.x()) / self._zoom + center.x() - self._pan_offset.x()
        y = (widget_pos.y() - center.y()) / self._zoom + center.y() - self._pan_offset.y()
        
        # Convert from display to frame coords
        if not display_rect.contains(int(x), int(y)):
            return None
        
        scale_x = self._frame_size.width() / display_rect.width()
        scale_y = self._frame_size.height() / display_rect.height()
        
        frame_x = int((x - display_rect.x()) * scale_x)
        frame_y = int((y - display_rect.y()) * scale_y)
        
        return (frame_x, frame_y)
    
    def _check_detection_hover(self, widget_pos: QPoint):
        """Check if mouse is hovering over a detection."""
        frame_coords = self._widget_to_frame_coords(widget_pos)
        if not frame_coords:
            self.detection_hovered.emit({})
            return
        
        fx, fy = frame_coords
        
        for det in self._detections:
            x, y, r = det.get("x", 0), det.get("y", 0), det.get("r_px", 0)
            
            # Check if inside circle
            dist_sq = (fx - x) ** 2 + (fy - y) ** 2
            if dist_sq <= r ** 2:
                self.detection_hovered.emit(det)
                return
        
        self.detection_hovered.emit({})
    
    def resizeEvent(self, event: QResizeEvent):
        """Handle resize."""
        super().resizeEvent(event)
        self.update()
