from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QImage
from PyQt6.QtCore import Qt
from mill_presenter.core.overlay import OverlayRenderer
from mill_presenter.core.models import FrameDetections
from typing import Optional, Set

class VideoWidget(QOpenGLWidget):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.renderer = OverlayRenderer(config)
        self.current_image: Optional[QImage] = None
        self.current_detections: Optional[FrameDetections] = None
        self.visible_classes: Set[int] = {4, 6, 8, 10} # Default all visible

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
        else:
            # Draw placeholder or background
            painter.fillRect(self.rect(), Qt.GlobalColor.black)
