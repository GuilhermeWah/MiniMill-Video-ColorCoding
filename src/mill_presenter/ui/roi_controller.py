from PyQt6.QtGui import QImage, QPainter, QColor, QPen
from PyQt6.QtCore import Qt, QPoint
import os
import cv2
import numpy as np

class ROIController:
    def __init__(self, widget):
        self.widget = widget
        self.is_active = False
        self.mask_image: QImage = None
        
        # Circle Mode State
        self.center_point = None
        self.current_radius = 0
        self.is_dragging = False
        self.is_moving = False
        self.move_offset = QPoint(0, 0)

    def start(self):
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
                self.auto_detect_mill()
            
        if hasattr(self.widget, 'set_interaction_mode'):
            self.widget.set_interaction_mode('roi')
            self.widget.set_roi_mask(self.mask_image)
            
        # If we have a circle (from auto-detect or previous), update mask
        if self.center_point:
            self._update_mask()

    def auto_detect_mill(self):
        """Attempts to automatically find the mill drum circle."""
        if not self.widget or not self.widget.current_image:
            return

        try:
            # Convert QImage to numpy array
            qimg = self.widget.current_image
            qimg = qimg.convertToFormat(QImage.Format.Format_RGB888)
            
            width = qimg.width()
            height = qimg.height()
            
            ptr = qimg.bits()
            ptr.setsize(height * width * 3)
            arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 3))
            
            # Preprocess
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            gray = cv2.medianBlur(gray, 5)
            
            # HoughCircles for the drum (large circle)
            # We expect the drum to be roughly centered and large (e.g. > 30% of height)
            min_r = int(min(width, height) * 0.35)
            max_r = int(min(width, height) * 0.48) # Slightly less than half
            
            circles = cv2.HoughCircles(
                gray, 
                cv2.HOUGH_GRADIENT, 
                dp=1, 
                minDist=min_r, # Only expect one main drum
                param1=50, 
                param2=30, 
                minRadius=min_r, 
                maxRadius=max_r
            )
            
            if circles is not None:
                circles = np.uint16(np.around(circles))
                # Take the strongest/largest circle
                best_circle = circles[0][0]
                cx, cy, r = int(best_circle[0]), int(best_circle[1]), int(best_circle[2])
                
                # Apply slightly smaller radius to be safe (inside the rim)
                safe_r = int(r * 0.96) 
                
                self.center_point = QPoint(cx, cy)
                self.current_radius = safe_r
                print(f"Auto-detected mill at ({cx}, {cy}) r={safe_r}")
                
        except Exception as e:
            print(f"Auto-detect failed: {e}")

    def cancel(self):
        self.is_active = False
        if hasattr(self.widget, 'set_interaction_mode'):
            self.widget.set_interaction_mode('none')
            # Clear the mask overlay from the widget so it doesn't persist
            self.widget.set_roi_mask(None)

    def handle_mouse_press(self, x: int, y: int, left_button: bool):
        if not self.is_active or not self.mask_image:
            return
        
        if not left_button:
             # Reset
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
            
            # Zone 2: Rim (Resize) - Outer 30% or slightly outside (+30px tolerance)
            if dist < self.current_radius + 30:
                self.is_dragging = True
                # We keep the existing center_point, so dragging will just update the radius
                return

        # Otherwise, start defining a NEW circle center
        self.center_point = click_point
        self.current_radius = 0
        self.is_dragging = True
        
        self._update_mask()

    def handle_mouse_move(self, x: int, y: int):
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
        self.is_dragging = False
        self.is_moving = False
        # Circle is now defined.

    def _update_mask(self):
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
            
            # Draw a helper outline so the user can see the boundary clearly
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(Qt.GlobalColor.yellow, 2, Qt.PenStyle.DashLine))
            painter.drawEllipse(self.center_point, self.current_radius, self.current_radius)
            
            painter.end()
            
        self.widget.update()

    def save(self, path: str):
        if not self.mask_image:
            return
            
        # Create a robust binary mask for the Vision Pipeline
        # We want: White (255) = Valid (Inside Circle), Black (0) = Ignore (Outside)
        
        width = self.mask_image.width()
        height = self.mask_image.height()
        
        # 1. Create a black canvas (Ignore everything)
        final_mask = QImage(width, height, QImage.Format.Format_Grayscale8)
        final_mask.fill(QColor(0, 0, 0)) # Black
        
        # 2. Draw the White Circle (Valid Region) if defined
        if self.center_point and self.current_radius > 0:
            painter = QPainter(final_mask)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False) # Aliasing is fine for masks
            painter.setBrush(QColor(255, 255, 255)) # White Fill
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(self.center_point, self.current_radius, self.current_radius)
            painter.end()
            
        final_mask.save(path)

    def is_point_valid(self, x, y):
        if not self.mask_image:
            return True
        # Check pixel alpha
        # If alpha > 0, it's masked (Ignore) -> Invalid
        if 0 <= x < self.mask_image.width() and 0 <= y < self.mask_image.height():
            c = self.mask_image.pixelColor(int(x), int(y))
            return c.alpha() == 0
        return True
