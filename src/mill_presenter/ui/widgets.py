from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QImage, QPen, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
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
        
        self.interaction_mode = 'none' # 'none', 'calibration', 'roi'
        self.calibration_points: List[Tuple[float, float]] = []
        self.roi_mask: Optional[QImage] = None

    def set_interaction_mode(self, mode: str):
        self.interaction_mode = mode
        self.setMouseTracking(mode != 'none')
        self.update()

    def set_calibration_points(self, points: List[Tuple[float, float]]):
        self.calibration_points = points
        self.update()

    def set_roi_mask(self, mask: QImage):
        self.roi_mask = mask
        self.update()

    def _widget_to_image_coords(self, pos) -> Tuple[float, float]:
        if not self.current_image:
            return -1, -1
            
        target_rect = self.rect()
        scaled_image = self.current_image.scaled(
            target_rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        x_offset = (target_rect.width() - scaled_image.width()) // 2
        y_offset = (target_rect.height() - scaled_image.height()) // 2
        
        scale = 1.0
        if self.current_image.width() > 0:
            scale = scaled_image.width() / self.current_image.width()
            
        click_x = pos.x() - x_offset
        click_y = pos.y() - y_offset
        
        img_x = click_x / scale
        img_y = click_y / scale
        
        return img_x, img_y

    def mousePressEvent(self, event):
        if self.interaction_mode == 'none' or not self.current_image:
            super().mousePressEvent(event)
            return

        img_x, img_y = self._widget_to_image_coords(event.pos())
        
        if 0 <= img_x < self.current_image.width() and 0 <= img_y < self.current_image.height():
            self.clicked.emit(img_x, img_y)
            self.mouse_pressed.emit(img_x, img_y, event.button() == Qt.MouseButton.LeftButton)

    def mouseMoveEvent(self, event):
        if self.interaction_mode == 'none' or not self.current_image:
            super().mouseMoveEvent(event)
            return
            
        img_x, img_y = self._widget_to_image_coords(event.pos())
        if 0 <= img_x < self.current_image.width() and 0 <= img_y < self.current_image.height():
            self.mouse_moved.emit(img_x, img_y)

    def mouseReleaseEvent(self, event):
        if self.interaction_mode == 'none' or not self.current_image:
            super().mouseReleaseEvent(event)
            return
            
        img_x, img_y = self._widget_to_image_coords(event.pos())
        if 0 <= img_x < self.current_image.width() and 0 <= img_y < self.current_image.height():
            self.mouse_released.emit(img_x, img_y)

    def set_frame(self, image: QImage, detections: Optional[FrameDetections]):
        self.current_image = image
        self.current_detections = detections
        self.update() # Trigger repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        
        if self.current_image:
            # Draw video frame
            # Scale image to fit widget while maintaining aspect ratio
            target_rect = self.rect()
            scaled_image = self.current_image.scaled(
                target_rect.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Center the image
            x = (target_rect.width() - scaled_image.width()) // 2
            y = (target_rect.height() - scaled_image.height()) // 2
            
            painter.drawImage(x, y, scaled_image)
            
            # Calculate scale factor for overlays
            # Original image width vs Scaled image width
            if self.current_image.width() > 0:
                scale = scaled_image.width() / self.current_image.width()
            else:
                scale = 1.0
            
            # Translate painter to image origin
            painter.translate(x, y)
            
            # Draw overlays
            if self.current_detections:
                self.renderer.draw(painter, self.current_detections, self.visible_classes, scale)
                
            # Draw ROI Mask
            if self.roi_mask:
                # Scale mask to fit
                # The mask is same size as original image
                # We need to draw it scaled
                # QPainter.drawImage handles scaling if we specify target rect
                # But we already translated painter to (x,y) and scaled? No, we translated to (x,y).
                # We need to draw the mask at (0,0) with size (scaled_image.width(), scaled_image.height())
                
                # Actually, we can just draw it.
                # But wait, the mask is ARGB.
                # We want to draw it scaled.
                
                target_w = scaled_image.width()
                target_h = scaled_image.height()
                painter.drawImage(
                    0, 0, 
                    self.roi_mask.scaled(target_w, target_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
                )

            # Draw Calibration UI
            if self.interaction_mode == 'calibration' and self.calibration_points:
                painter.setPen(QPen(Qt.GlobalColor.cyan, 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                
                # Draw points
                for px, py in self.calibration_points:
                    painter.drawEllipse(QPointF(px * scale, py * scale), 5, 5)
                    
                # Draw line if 2 points
                if len(self.calibration_points) == 2:
                    p1 = self.calibration_points[0]
                    p2 = self.calibration_points[1]
                    painter.drawLine(
                        QPointF(p1[0] * scale, p1[1] * scale),
                        QPointF(p2[0] * scale, p2[1] * scale)
                    )
        else:
            # Draw placeholder or background
            painter.fillRect(self.rect(), Qt.GlobalColor.black)
