"""
Drum Calibration Controller - Auto-detects the drum outer edge for px_per_mm calibration.

This controller:
1. Auto-detects the drum's outer edge on app startup
2. Shows the calibration circle for user confirmation/adjustment
3. User can drag to resize or move the circle
4. Once confirmed, calculates px_per_mm from the known drum diameter (200mm)
"""
from PyQt6.QtGui import QImage, QPainter, QColor, QPen
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import QMessageBox
import cv2
import numpy as np


class DrumCalibrationController:
    def __init__(self, widget, config: dict):
        self.widget = widget
        self.config = config
        self.is_active = False
        self.calibration_confirmed = False
        
        # Read drum diameter from config (default 196mm)
        self.drum_diameter_mm = config.get('calibration', {}).get('drum_diameter_mm', 196.0)
        
        # Circle state
        self.center_point = None
        self.current_radius = 0
        self.confidence = 0.0  # Quality indicator 0.0 - 1.0
        
        # Interaction state
        self.is_dragging = False
        self.is_moving = False
        self.move_offset = QPoint(0, 0)
        
        # Overlay image
        self.overlay_image: QImage = None
        
        # Callback
        self.on_calibration_confirmed = None
    
    def auto_detect_and_show(self):
        """Called on app startup - auto-detect drum and show for confirmation."""
        if not self.widget or not self.widget.current_image:
            return False
        
        self.is_active = True
        self.calibration_confirmed = False
        
        # Create overlay
        self._init_overlay()
        
        # Auto-detect using multi-frame averaging if video is available
        self._auto_detect_drum()
        
        if self.center_point:
            self._update_overlay()
            if hasattr(self.widget, 'set_interaction_mode'):
                self.widget.set_interaction_mode('drum_calibration')
                self.widget.set_drum_calibration_overlay(self.overlay_image)
            return True
        
        return False
        
    def _init_overlay(self):
        if self.widget.current_image:
            width = self.widget.current_image.width()
            height = self.widget.current_image.height()
            self.overlay_image = QImage(width, height, QImage.Format.Format_ARGB32)
            self.overlay_image.fill(Qt.GlobalColor.transparent)

    def _get_frame_cv(self, qimg: QImage) -> np.ndarray:
        """Convert QImage to RGB numpy array for OpenCV."""
        width = qimg.width()
        height = qimg.height()
        
        # Handle format
        if qimg.format() != QImage.Format.Format_RGB888:
            qimg = qimg.convertToFormat(QImage.Format.Format_RGB888)
            
        ptr = qimg.bits()
        ptr.setsize(height * width * 3)
        return np.array(ptr).reshape(height, width, 3)

    def _detect_circle_in_frame(self, frame_bgr: np.ndarray):
        """Run single-frame Hough detection."""
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)
        
        rows = gray.shape[0]
        # Hough params
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=rows // 2,  # Assume only one main drum
            param1=50,
            param2=30,
            minRadius=rows // 4,
            maxRadius=rows // 2 + 100
        )
        
        if circles is not None:
             circles = np.uint16(np.around(circles))
             # Take largest by radius (index 2)
             largest_idx = np.argmax(circles[0, :, 2])
             return circles[0][largest_idx] # (x, y, r)
        return None

    def _auto_detect_drum(self):
        """Detect drum averaging multiple frames if available."""
        # Try to gather multiple frames from the frame_loader if possible
        # We need access to the MainWindow's frame_loader really, but standard widget access 
        # might be limited. We'll verify if we can access it via the widget parent chain,
        # or just fallback to single current frame.
        
        frames_to_process = []
        
        # 1. Add current frame
        if self.widget.current_image:
             frames_to_process.append(self._get_frame_cv(self.widget.current_image))
             
        # TODO: Ideally we'd actually fetch 5 frames here from the loader
        # For now, we will use the single frame but implement the sub-pixel refinement
        # which is the biggest gain.
        
        candidates = []
        for frame in frames_to_process:
            circ = self._detect_circle_in_frame(frame)
            if circ is not None:
                candidates.append(circ)
        
        if not candidates:
            self._fallback_default()
            return
            
        # Average results (mock averaging since we likely only have 1 frame for now without
        # deeper refactoring to pass frame_loader access)
        avg_x = np.mean([c[0] for c in candidates])
        avg_y = np.mean([c[1] for c in candidates])
        avg_r = np.mean([c[2] for c in candidates])
        
        # Refine using Canny Edge check
        final_x, final_y, final_r, conf = self._refine_circle_edges(frames_to_process[0], avg_x, avg_y, avg_r)
        
        self.center_point = QPoint(int(final_x), int(final_y))
        self.current_radius = int(final_r)
        self.confidence = conf
        
        print(f"Drum Auto-Detect: ({final_x:.1f}, {final_y:.1f}) r={final_r:.1f} conf={conf:.2f}")

    def _get_radial_edges(self, gray, cx, cy, r_guess, search_margin=40):
        """Sample points along radial lines to find exact edge."""
        points = []
        h, w = gray.shape[:2]
        
        # Sample angles
        for angle_deg in range(0, 360, 5): 
            theta = np.deg2rad(angle_deg)
            # Search along this ray
            x0 = int(cx + (r_guess - search_margin) * np.cos(theta))
            y0 = int(cy + (r_guess - search_margin) * np.sin(theta))
            x1 = int(cx + (r_guess + search_margin) * np.cos(theta))
            y1 = int(cy + (r_guess + search_margin) * np.sin(theta))
            
            # Manual line sampling (cv2.sampleLine doesn't exist in all versions)
            num_points = int(np.sqrt((x1-x0)**2 + (y1-y0)**2))
            if num_points < 3:
                continue
            xs = np.linspace(x0, x1, num_points).astype(int)
            ys = np.linspace(y0, y1, num_points).astype(int)
            
            # Clamp to image bounds
            xs = np.clip(xs, 0, w-1)
            ys = np.clip(ys, 0, h-1)
            
            # Sample pixel values along line
            profile = gray[ys, xs]
            if len(profile) < 3:
                continue
                
            # Find strongest gradient in profile
            grads = np.abs(np.gradient(profile.astype(float)))
            max_grad_idx = np.argmax(grads)
            
            if grads[max_grad_idx] > 20: # Threshold noise
                # Interpolate exact pos
                ratio = max_grad_idx / len(profile)
                exact_x = x0 + (x1 - x0) * ratio
                exact_y = y0 + (y1 - y0) * ratio
                points.append((exact_x, exact_y))
                
        return points

    def _refine_circle_edges(self, frame, x_est, y_est, r_est):
        """Refine circle estimate using edge sampling and fitting."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # Expect RGB frame here if passed from _get_frame_cv which does convert
        if len(gray.shape) == 3: # Double check
             gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        
        edge_points = self._get_radial_edges(gray, x_est, y_est, r_est, search_margin=30)
        
        if len(edge_points) < 10:
             return x_est, y_est, r_est, 0.4 # Low confidence, keep guess
             
        # Fit circle to points
        pts = np.array(edge_points, dtype=np.float32)
        # Solve least squares (x-xc)^2 + (y-yc)^2 = r^2
        # Simplified: Use OpenCV minEnclosingCircle (actually we want fit, not enclosing)
        # Better: fitEllipse but force circle?
        # Standard: Least squares circle fit
        
        A = np.c_[2*pts[:,0], 2*pts[:,1], np.ones(len(pts))]
        b = pts[:,0]**2 + pts[:,1]**2
        try:
             sol, residuals, _, _ = np.linalg.lstsq(A, b, rcond=None)
             cx, cy, c_term = sol
             r = np.sqrt(c_term + cx**2 + cy**2)
             
             # Calculate residual error (quality metric)
             err = np.sqrt(residuals[0] / len(pts)) if len(residuals) > 0 and residuals[0] > 0 else 10.0
             conf = max(0.0, min(1.0, 1.0 - (err / 10.0))) # Rough map err to 0..1
             
             # Sanity check - don't deviate too far from guess
             if abs(r - r_est) > 50 or abs(cx - x_est) > 50 or abs(cy - y_est) > 50:
                 return x_est, y_est, r_est, 0.3 # Reject wild fit
                 
             return cx, cy, r, conf
        except:
             return x_est, y_est, r_est, 0.4

    def _fallback_default(self):
         width = self.widget.current_image.width()
         height = self.widget.current_image.height()
         self.center_point = QPoint(width // 2, height // 2)
         self.current_radius = min(width, height) // 3
         self.confidence = 0.0

    def _update_overlay(self):
        """Draw the calibration circle overlay."""
        if not self.overlay_image or not self.center_point:
            return
        
        self.overlay_image.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(self.overlay_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Color based on confidence
        if self.confidence > 0.8:
            col = QColor(0, 255, 100, 200) # Green best
        elif self.confidence > 0.5:
             col = QColor(255, 255, 0, 200) # Yellow ok
        else:
             col = QColor(255, 50, 50, 200) # Red poor
             
        pen = QPen(col, 3)
        painter.setPen(pen)
        painter.drawEllipse(self.center_point, self.current_radius, self.current_radius)
        
        # Crosshair
        cx, cy = self.center_point.x(), self.center_point.y()
        painter.drawLine(cx - 15, cy, cx + 15, cy)
        painter.drawLine(cx, cy - 15, cx, cy + 15)
        
        # Handles
        handle_pen = QPen(col, 2)
        painter.setPen(handle_pen)
        painter.setBrush(QColor(0,0,0,100))
        handle_size = 8
        painter.drawEllipse(QPoint(int(cx + self.current_radius), int(cy)), handle_size, handle_size)
        painter.drawEllipse(QPoint(int(cx), int(cy + self.current_radius)), handle_size, handle_size)
        
        # Text Info
        px_per_mm = self._calculate_px_per_mm()
        label = f"Drum: {self.current_radius * 2}px = {self.drum_diameter_mm}mm"
        label2 = f"px_per_mm = {px_per_mm:.2f}"
        label3 = f"Quality: {int(self.confidence * 100)}%"
        
        # Background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 180))
        painter.drawRect(cx - 100, cy - self.current_radius - 70, 200, 65)
        
        # Draw Text
        painter.setPen(QColor(0, 255, 255))
        font = painter.font()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(cx - 95, cy - self.current_radius - 50, label)
        painter.drawText(cx - 95, cy - self.current_radius - 30, label2)
        
        # Quality color
        painter.setPen(col)
        painter.drawText(cx - 95, cy - self.current_radius - 10, label3)
        
        painter.end()
        
        if hasattr(self.widget, 'set_drum_calibration_overlay'):
            self.widget.set_drum_calibration_overlay(self.overlay_image)
    
    def _calculate_px_per_mm(self) -> float:
        if self.current_radius <= 0: return 1.0
        return (2 * self.current_radius) / self.drum_diameter_mm
    
    def handle_mouse_press(self, pos: QPoint):
        if not self.is_active or not self.center_point: return
        dist_to_center = ((pos.x() - self.center_point.x()) ** 2 + 
                          (pos.y() - self.center_point.y()) ** 2) ** 0.5
        dist_to_edge = abs(dist_to_center - self.current_radius)
        
        if dist_to_center < 30:
            self.is_moving = True
            self.move_offset = pos - self.center_point
        elif dist_to_edge < 20:
            self.is_dragging = True
    
    def handle_mouse_move(self, pos: QPoint):
        if not self.is_active: return
        if self.is_moving and self.center_point:
            self.center_point = pos - self.move_offset
            self._update_overlay()
        elif self.is_dragging and self.center_point:
            dx = pos.x() - self.center_point.x()
            dy = pos.y() - self.center_point.y()
            new_r = int((dx**2 + dy**2)**0.5)
            if new_r > 50:
                self.current_radius = new_r
                self._update_overlay()
    
    def handle_mouse_release(self, pos: QPoint):
        self.is_dragging = False
        self.is_moving = False
        
    def confirm(self):
        if not self.center_point or self.current_radius <= 0: return
        px_per_mm = self._calculate_px_per_mm()
        
        if 'calibration' not in self.config: self.config['calibration'] = {}
        self.config['calibration']['px_per_mm'] = px_per_mm
        
        print(f"Calibration confirmed: px_per_mm = {px_per_mm:.3f}")
        self.calibration_confirmed = True
        self.is_active = False
        
        # Clean up
        if hasattr(self.widget, 'set_drum_calibration_overlay'):
             self.widget.set_drum_calibration_overlay(None)
        if hasattr(self.widget, 'set_interaction_mode'):
             self.widget.set_interaction_mode('none')
             
        if self.on_calibration_confirmed:
            self.on_calibration_confirmed(px_per_mm, self.center_point, self.current_radius)
            
    def cancel(self):
        self.is_active = False
        self.calibration_confirmed = False
        if hasattr(self.widget, 'set_drum_calibration_overlay'):
             self.widget.set_drum_calibration_overlay(None)
        if hasattr(self.widget, 'set_interaction_mode'):
             self.widget.set_interaction_mode('none')

    def get_roi_suggestion(self) -> tuple:
         if self.center_point and self.current_radius > 0:
             return self.center_point, int(self.current_radius * 0.85)
         return None, 0
