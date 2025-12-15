from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QImage, QPen, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF
from mill_presenter.core.overlay import OverlayRenderer
from mill_presenter.core.models import FrameDetections
from typing import Optional, Set, List, Tuple

class VideoWidget(QOpenGLWidget):
    
    clicked = pyqtSignal(float, float) # Emits (x, y) in image coordinates
    mouse_pressed = pyqtSignal(float, float, bool) # x, y, is_left
    mouse_moved = pyqtSignal(float, float) # x, y
    mouse_released = pyqtSignal(float, float) # x, y

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.renderer = OverlayRenderer(config)
        self.current_image: Optional[QImage] = None
        self.current_detections: Optional[FrameDetections] = None
        self.visible_classes: Set[int] = {4, 6, 8, 10} # Default all visible
        
        self.interaction_mode = 'none' # 'none', 'calibration', 'roi', 'drum_calibration'
        self.calibration_points: List[Tuple[float, float]] = []
        self.roi_mask: Optional[QImage] = None
        self.drum_calibration_overlay: Optional[QImage] = None  # For drum auto-detect
        
        # Zoom & Pan State
        self.zoom_scale = 1.0
        self.pan_pos = QPointF(0, 0)
        self.is_panning = False
        self.last_mouse_pos = QPointF()

    def set_interaction_mode(self, mode: str):
        self.interaction_mode = mode
        self.setMouseTracking(mode != 'none')
        self.update()

    def set_calibration_points(self, points: List[Tuple[float, float]]):
        self.calibration_points = points
        self.update()

    def set_roi_mask(self, mask: Optional[QImage]):
        self.roi_mask = mask
        self.update()

    def set_drum_calibration_overlay(self, overlay: Optional[QImage]):
        """Set the drum calibration overlay image."""
        self.drum_calibration_overlay = overlay
        self.update()

    def _get_base_transform_params(self):
        """Calculates the base scaling and offset to fit image in widget."""
        if not self.current_image:
            return 1.0, 0.0, 0.0
            
        widget_w = self.width()
        widget_h = self.height()
        img_w = self.current_image.width()
        img_h = self.current_image.height()
        
        if img_w == 0 or img_h == 0: return 1.0, 0.0, 0.0

        scale_w = widget_w / img_w
        scale_h = widget_h / img_h
        base_scale = min(scale_w, scale_h)
        
        base_dx = (widget_w - img_w * base_scale) / 2
        base_dy = (widget_h - img_h * base_scale) / 2
        
        return base_scale, base_dx, base_dy

    def _widget_to_image_coords(self, pos) -> Tuple[float, float]:
        if not self.current_image:
            return -1, -1
            
        base_scale, base_dx, base_dy = self._get_base_transform_params()
        
        # Reverse Transform:
        # Screen -> (Remove Pan) -> (Remove Zoom around Center) -> (Remove Base Offset) -> (Remove Base Scale)
        
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        # 1. Relative to center, remove pan
        rel_x = pos.x() - (center_x + self.pan_pos.x())
        rel_y = pos.y() - (center_y + self.pan_pos.y())
        
        # 2. Remove Zoom
        unzoomed_x = rel_x / self.zoom_scale
        unzoomed_y = rel_y / self.zoom_scale
        
        # 3. Back to widget coords (unzoomed)
        widget_x = unzoomed_x + center_x
        widget_y = unzoomed_y + center_y
        
        # 4. Remove Base Fit
        img_x = (widget_x - base_dx) / base_scale
        img_y = (widget_y - base_dy) / base_scale
        
        return img_x, img_y

    def wheelEvent(self, event):
        if not self.current_image:
            return
            
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9
        
        self.zoom_scale *= zoom_factor
        
        # Clamp zoom
        self.zoom_scale = max(1.0, min(self.zoom_scale, 20.0))
        
        # If zooming out to 1.0, reset pan
        if self.zoom_scale <= 1.01:
            self.zoom_scale = 1.0
            self.pan_pos = QPointF(0, 0)
            
        self.update()

    def mousePressEvent(self, event):
        # Handle Panning
        # Middle Button: Always Pan
        # Left Button: Pan only if mode is 'none' (Standard drag-to-pan)
        if event.button() == Qt.MouseButton.MiddleButton or \
           (event.button() == Qt.MouseButton.LeftButton and self.interaction_mode == 'none'):
            self.is_panning = True
            self.last_mouse_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if self.interaction_mode == 'none' or not self.current_image:
            super().mousePressEvent(event)
            return

        img_x, img_y = self._widget_to_image_coords(event.pos())
        
        if 0 <= img_x < self.current_image.width() and 0 <= img_y < self.current_image.height():
            self.clicked.emit(img_x, img_y)
            self.mouse_pressed.emit(img_x, img_y, event.button() == Qt.MouseButton.LeftButton)

    def mouseMoveEvent(self, event):
        # Handle Panning
        if self.is_panning:
            delta = event.position() - self.last_mouse_pos
            self.pan_pos += delta
            self.last_mouse_pos = event.position()
            self.update()
            return

        if self.interaction_mode == 'none' or not self.current_image:
            super().mouseMoveEvent(event)
            return
            
        img_x, img_y = self._widget_to_image_coords(event.pos())
        # Allow moving outside image bounds for some tools? 
        # ROI tool might need to drag outside.
        # But let's keep the check for now, or relax it.
        # ROI tool handles dragging.
        self.mouse_moved.emit(img_x, img_y)

    def mouseReleaseEvent(self, event):
        if self.is_panning and (event.button() == Qt.MouseButton.MiddleButton or event.button() == Qt.MouseButton.LeftButton):
            self.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        if self.interaction_mode == 'none' or not self.current_image:
            super().mouseReleaseEvent(event)
            return
            
        img_x, img_y = self._widget_to_image_coords(event.pos())
        self.mouse_released.emit(img_x, img_y)

    def set_frame(self, image: QImage, detections: Optional[FrameDetections]):
        self.current_image = image
        self.current_detections = detections
        self.update() # Trigger repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        
        if not self.current_image:
            return

        base_scale, base_dx, base_dy = self._get_base_transform_params()
        
        painter.save()
        
        # Apply Zoom/Pan Transform
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        painter.translate(center_x + self.pan_pos.x(), center_y + self.pan_pos.y())
        painter.scale(self.zoom_scale, self.zoom_scale)
        painter.translate(-center_x, -center_y)
        
        # Apply Base Fit Transform (Move to Image Space)
        painter.translate(base_dx, base_dy)
        painter.scale(base_scale, base_scale)
        
        # Now we are in Image Coordinates! (0,0) is top-left of image, 1 unit = 1 pixel
        
        # Draw Video Frame
        # Since we are in Image Coords, we draw at (0,0) with size (w, h)
        target_rect = QRectF(0, 0, self.current_image.width(), self.current_image.height())
        painter.drawImage(target_rect, self.current_image)
        
        # Draw Overlays (scale=1.0 because painter is already scaled)
        if self.current_detections:
            self.renderer.draw(painter, self.current_detections, self.visible_classes, 1.0)
            
        # Draw ROI Mask
        if self.roi_mask:
            painter.drawImage(target_rect, self.roi_mask)

        # Draw Drum Calibration Overlay
        if self.drum_calibration_overlay:
            painter.drawImage(target_rect, self.drum_calibration_overlay)

        # Draw Calibration UI
        if self.interaction_mode == 'calibration' and self.calibration_points:
            painter.setPen(QPen(Qt.GlobalColor.cyan, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            # Draw points
            for px, py in self.calibration_points:
                painter.drawEllipse(QPointF(px, py), 5, 5)
                
            # Draw line if 2 points
            if len(self.calibration_points) == 2:
                p1 = self.calibration_points[0]
                p2 = self.calibration_points[1]
                painter.drawLine(QPointF(p1[0], p1[1]), QPointF(p2[0], p2[1]))
                
        painter.restore()
