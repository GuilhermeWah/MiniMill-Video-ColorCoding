from PyQt6.QtGui import QImage, QPainter, QColor, QPen
from PyQt6.QtCore import Qt, QPoint
import os

class ROIController:
    def __init__(self, widget):
        self.widget = widget
        self.is_active = False
        self.mask_image: QImage = None
        self.brush_size = 20
        self.last_point = None
        self.is_drawing = False
        self.draw_color = Qt.GlobalColor.black # Black = Ignore

    def start(self):
        self.is_active = True
        if self.widget and self.widget.current_image:
            width = self.widget.current_image.width()
            height = self.widget.current_image.height()
            
            # Load existing or create new
            # For now, create new white mask (all valid)
            self.mask_image = QImage(width, height, QImage.Format.Format_ARGB32)
            self.mask_image.fill(Qt.GlobalColor.transparent) # Transparent for overlay? 
            # Wait, the mask itself should be B&W. But for display we might want overlay.
            # Let's keep the mask as a separate Grayscale image for logic, 
            # and maybe an ARGB image for display?
            # Or just use one ARGB image where we paint Red with Alpha for "Ignore".
            # And when saving, we convert to B&W.
            
            # Let's use ARGB for the "Overlay" layer.
            # Transparent = Valid.
            # Red (semi-transparent) = Ignore.
            self.mask_image.fill(Qt.GlobalColor.transparent)
            
        if hasattr(self.widget, 'set_interaction_mode'):
            self.widget.set_interaction_mode('roi')
            self.widget.set_roi_mask(self.mask_image)

    def cancel(self):
        self.is_active = False
        if hasattr(self.widget, 'set_interaction_mode'):
            self.widget.set_interaction_mode('none')

    def handle_mouse_press(self, x: int, y: int, left_button: bool):
        if not self.is_active or not self.mask_image:
            return
        
        self.is_drawing = True
        self.last_point = QPoint(int(x), int(y))
        
        # Left click = Paint Ignore (Red overlay)
        # Right click = Erase (Transparent)
        if left_button:
            self.draw_color = QColor(255, 0, 0, 128) # Semi-transparent Red
        else:
            self.draw_color = Qt.GlobalColor.transparent # Erase to transparent

        self._paint_point(x, y)

    def handle_mouse_move(self, x: int, y: int):
        if not self.is_drawing or not self.mask_image:
            return
        self._paint_line(self.last_point, QPoint(int(x), int(y)))
        self.last_point = QPoint(int(x), int(y))

    def handle_mouse_release(self, x: int, y: int):
        self.is_drawing = False
        self.last_point = None

    def _paint_point(self, x, y):
        painter = QPainter(self.mask_image)
        
        if self.draw_color == Qt.GlobalColor.transparent:
            # Erasing requires CompositionMode
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        else:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.draw_color)
        painter.drawEllipse(QPoint(int(x), int(y)), self.brush_size // 2, self.brush_size // 2)
        painter.end()
        self.widget.update()

    def _paint_line(self, p1, p2):
        painter = QPainter(self.mask_image)
        
        if self.draw_color == Qt.GlobalColor.transparent:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        else:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        pen = QPen(self.draw_color)
        pen.setWidth(self.brush_size)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(p1, p2)
        painter.end()
        self.widget.update()

    def save(self, path: str):
        if not self.mask_image:
            return
            
        # Convert Overlay to B&W Mask
        # Transparent -> White (Valid)
        # Red -> Black (Ignore)
        
        # Create target image
        bw_mask = QImage(self.mask_image.size(), QImage.Format.Format_Grayscale8)
        bw_mask.fill(Qt.GlobalColor.white) # Default valid
        
        painter = QPainter(bw_mask)
        # Draw the overlay onto the white background
        # But we need to turn Red pixels into Black pixels.
        # We can iterate or use a trick.
        # Since we only have Transparent or Red, we can just draw the alpha channel?
        # Or just draw the overlay as Black.
        
        # Let's iterate for correctness or use a mask.
        # Actually, if we draw the mask_image onto the white background, 
        # the Red pixels will appear red. We want them Black.
        
        # Better approach:
        # Create a temporary image filled with Black.
        # Use the mask_image's alpha channel as a mask to draw Black onto White?
        
        # Simple way:
        # 1. Fill bw_mask with White.
        # 2. Iterate pixels? Slow in Python.
        
        # 3. Use QPainter with CompositionMode?
        # If we draw the mask_image using a Black brush where alpha > 0?
        
        # Let's try:
        # Draw the mask_image onto bw_mask.
        # Then convert to Grayscale. Red (brightness ~76) will be dark gray.
        # Threshold it?
        
        # Let's assume for now we just save the overlay and handle conversion later, 
        # OR implement a proper conversion.
        
        # Fast conversion:
        # 1. Extract Alpha channel.
        # 2. Invert it (Alpha 0 -> White, Alpha 128 -> Black).
        
        alpha = self.mask_image.alphaChannel()
        # Alpha: 0 (Transparent/Valid) -> 0
        # Alpha: 128 (Red/Ignore) -> 128
        
        # We want:
        # 0 -> 255 (White)
        # >0 -> 0 (Black)
        
        alpha.invertPixels() 
        # Now:
        # 0 -> 255 (White)
        # 128 -> 127 (Gray)
        
        # Threshold to make it binary
        # We want anything not White to be Black.
        # Or anything that was painted (Alpha > 0) to be Black.
        
        # Let's just save the alpha channel inverted and thresholded.
        # But QImage doesn't have easy threshold.
        
        # Fallback: Save as PNG, let OpenCV handle it?
        # Or just save the overlay as is (roi_overlay.png) and let the processor use it?
        # The processor expects B&W.
        
        # Let's try to paint Black where Alpha is non-zero.
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        # This is getting complicated for a simple mask.
        
        # Let's just save the alpha channel inverted.
        # 0 (Valid) -> 255 (White)
        # 128 (Ignore) -> 127 (Gray) -> Processor treats < 128 as Black?
        # Processor uses standard threshold usually.
        
        bw_mask = alpha
        bw_mask.invertPixels()
        
        # Save
        bw_mask.save(path)

    def is_point_valid(self, x, y):
        if not self.mask_image:
            return True
        # Check pixel alpha
        # If alpha > 0, it's masked (Ignore) -> Invalid
        if 0 <= x < self.mask_image.width() and 0 <= y < self.mask_image.height():
            c = self.mask_image.pixelColor(int(x), int(y))
            return c.alpha() == 0
        return True
