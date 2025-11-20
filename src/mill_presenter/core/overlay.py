from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtCore import QPointF
from typing import Set, Dict
from mill_presenter.core.models import FrameDetections

class OverlayRenderer:
    """
    Handles drawing of detection overlays using QPainter.
    Designed to be used by both the UI Player (QOpenGLWidget) and the Exporter.
    """
    def __init__(self, config: dict):
        self.config = config
        self.line_width = config.get('overlay', {}).get('line_width', 2)
        colors_cfg = config.get('overlay', {}).get('colors', {})
        
        # Pre-allocate pens to avoid per-frame allocation
        self.pens: Dict[int, QPen] = {}
        for cls_id, hex_color in colors_cfg.items():
            # Ensure hex_color is a string
            if isinstance(hex_color, str):
                color = QColor(hex_color)
                pen = QPen(color)
                pen.setWidth(self.line_width)
                self.pens[cls_id] = pen

    def draw(self, painter: QPainter, detections: FrameDetections, visible_classes: Set[int], scale: float = 1.0):
        """
        Draws the detections onto the provided painter.
        
        Args:
            painter: The QPainter instance to draw on.
            detections: The FrameDetections object containing balls.
            visible_classes: A set of class IDs (int) that should be drawn.
            scale: Scaling factor (e.g., if video is scaled in UI).
        """
        if not detections or not detections.balls:
            return

        for ball in detections.balls:
            if ball.cls not in visible_classes:
                continue
            
            pen = self.pens.get(ball.cls)
            if pen:
                painter.setPen(pen)
                
                # Apply scaling
                x = ball.x * scale
                y = ball.y * scale
                r = ball.r_px * scale
                
                # Draw circle
                painter.drawEllipse(QPointF(x, y), r, r)
