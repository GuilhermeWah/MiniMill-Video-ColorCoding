# ROI Mask Controller - Defines the detection region

"""
ROIController - Creates a visual mask overlay for detection region.

Shows:
- Red = ignored area (outside drum)
- Transparent = valid area (inside drum)
- Yellow dashed circle = boundary

Interaction:
- Left click + drag center (inner 70%) = move the circle
- Left click + drag edge (outer 30%) = resize the circle
- Right click = reset
"""

from PySide6.QtGui import QImage, QPainter, QColor, QPen
from PySide6.QtCore import Qt, QPoint
import cv2
import numpy as np


class ROIController:
    def __init__(self, widget):
        self.widget = widget
        self.is_active = False
        self.mask_image: QImage = None
        
        # Circle state
        self.center_point = None
        self.current_radius = 0
        self.is_dragging = False
        self.is_moving = False
        self.move_offset = QPoint(0, 0)

    def start(self):
        """Enter ROI mask editing mode."""
        self.is_active = True
        if self.widget and self.widget.current_image:
            width = self.widget.current_image.width()
            height = self.widget.current_image.height()
            
            # Create a new mask layer
            self.mask_image = QImage(width, height, QImage.Format.Format_ARGB32)
            
            # Initialize with full Red (Ignore everything by default)
            self.mask_image.fill(QColor(255, 0, 0, 128))
            
            # Try auto-detect if no circle is defined
            if self.center_point is None:
                self._auto_detect_drum()
            
        if hasattr(self.widget, 'set_interaction_mode'):
            self.widget.set_interaction_mode('roi')
        if hasattr(self.widget, 'set_roi_mask'):
            self.widget.set_roi_mask(self.mask_image)
            
        # If we have a circle (from auto-detect or previous), update mask
        if self.center_point:
            self._update_mask()

    def _auto_detect_drum(self):
        """Automatically detect the drum circle."""
        if not self.widget or not self.widget.current_image:
            return

        try:
            # Convert QImage to numpy array
            qimg = self.widget.current_image
            qimg = qimg.convertToFormat(QImage.Format.Format_RGB888)
            
            width = qimg.width()
            height = qimg.height()
            
            # PySide6 compatible conversion
            bytes_per_line = qimg.bytesPerLine()
            ptr = qimg.constBits()
            arr = np.frombuffer(ptr, dtype=np.uint8).reshape(height, bytes_per_line)
            arr = arr[:, :width * 3].reshape(height, width, 3).copy()
            
            # Preprocess
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            gray = cv2.medianBlur(gray, 5)
            
            # HoughCircles for the drum (large circle)
            min_r = int(min(width, height) * 0.35)
            max_r = int(min(width, height) * 0.48)
            
            circles = cv2.HoughCircles(
                gray, 
                cv2.HOUGH_GRADIENT, 
                dp=1, 
                minDist=min_r,
                param1=50, 
                param2=30, 
                minRadius=min_r, 
                maxRadius=max_r
            )
            
            if circles is not None:
                circles = np.uint16(np.around(circles))
                best_circle = circles[0][0]
                cx, cy, r = int(best_circle[0]), int(best_circle[1]), int(best_circle[2])
                
                # Apply slightly smaller radius to be safe (inside the rim)
                safe_r = int(r * 0.96)
                
                self.center_point = QPoint(cx, cy)
                self.current_radius = safe_r
                print(f"Auto-detected drum at ({cx}, {cy}) r={safe_r}")
                
        except Exception as e:
            print(f"Auto-detect failed: {e}")

    def cancel(self):
        """Exit ROI mask editing mode without saving."""
        self.is_active = False
        if hasattr(self.widget, 'set_interaction_mode'):
            self.widget.set_interaction_mode('none')
        if hasattr(self.widget, 'set_roi_mask'):
            self.widget.set_roi_mask(None)

    def handle_mouse_press(self, x: int, y: int, left_button: bool = True):
        """Handle mouse press for circle manipulation."""
        if not self.is_active or not self.mask_image:
            return
        
        if not left_button:
            # Right click = Reset
            self.center_point = None
            self.current_radius = 0
            self._update_mask()
            return

        click_point = QPoint(int(x), int(y))

        # Check if we are interacting with an existing circle
        if self.center_point and self.current_radius > 0:
            dx = x - self.center_point.x()
            dy = y - self.center_point.y()
            dist = (dx**2 + dy**2)**0.5
            
            # Zone 1: Center (Move) - Inner 70%
            if dist < self.current_radius * 0.7:
                self.is_moving = True
                self.move_offset = click_point - self.center_point
                return
            
            # Zone 2: Rim (Resize) - Outer 30% or slightly outside
            if dist < self.current_radius + 30:
                self.is_dragging = True
                return

        # Otherwise, start defining a NEW circle center
        self.center_point = click_point
        self.current_radius = 0
        self.is_dragging = True
        self._update_mask()

    def handle_mouse_move(self, x: int, y: int):
        """Handle mouse movement for dragging."""
        current_point = QPoint(int(x), int(y))
        
        if self.is_moving and self.center_point:
            # Move the center
            self.center_point = current_point - self.move_offset
            self._update_mask()
            return

        if self.is_dragging and self.center_point:
            # Calculate radius
            dx = x - self.center_point.x()
            dy = y - self.center_point.y()
            self.current_radius = int((dx**2 + dy**2)**0.5)
            self._update_mask()

    def handle_mouse_release(self, x: int, y: int):
        """Handle mouse release."""
        self.is_dragging = False
        self.is_moving = False

    def _update_mask(self):
        """Update the visual mask overlay."""
        if not self.mask_image:
            return
            
        # Reset to full Red (Ignore)
        self.mask_image.fill(QColor(255, 0, 0, 128))
        
        if self.center_point and self.current_radius > 0:
            painter = QPainter(self.mask_image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Cut out the "Valid" circle (make it transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.setBrush(Qt.GlobalColor.transparent)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(self.center_point, self.current_radius, self.current_radius)
            
            # Draw a helper outline
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(Qt.GlobalColor.yellow, 2, Qt.PenStyle.DashLine))
            painter.drawEllipse(self.center_point, self.current_radius, self.current_radius)
            
            painter.end()
        
        if hasattr(self.widget, 'set_roi_mask'):
            self.widget.set_roi_mask(self.mask_image)
        self.widget.update()

    def save(self, path: str):
        """Save the mask as a PNG image for the pipeline."""
        if not self.mask_image:
            return
            
        width = self.mask_image.width()
        height = self.mask_image.height()
        
        # Create binary mask: White = Valid, Black = Ignore
        final_mask = QImage(width, height, QImage.Format.Format_Grayscale8)
        final_mask.fill(QColor(0, 0, 0))  # Black
        
        if self.center_point and self.current_radius > 0:
            painter = QPainter(final_mask)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            painter.setBrush(QColor(255, 255, 255))  # White
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(self.center_point, self.current_radius, self.current_radius)
            painter.end()
            
        final_mask.save(path)
        print(f"[ROI] Mask saved to {path}")

    def get_center_and_radius(self):
        """Return (center_point, radius) or (None, 0) if not defined."""
        if self.center_point and self.current_radius > 0:
            return self.center_point, self.current_radius
        return None, 0

    def is_point_valid(self, x: int, y: int) -> bool:
        """Check if a point is inside the valid region."""
        if not self.mask_image:
            return True
        if 0 <= x < self.mask_image.width() and 0 <= y < self.mask_image.height():
            c = self.mask_image.pixelColor(int(x), int(y))
            return c.alpha() == 0  # Transparent = valid
        return True
