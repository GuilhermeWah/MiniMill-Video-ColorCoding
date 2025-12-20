# MillPresenter — Calibration Controller

"""
Point-to-point calibration tool for accurate px_per_mm calculation.

Workflow:
1. User clicks "Calibrate" button
2. User clicks Point A on the video frame
3. User clicks Point B on the video frame
4. Dialog prompts for known distance in mm
5. px_per_mm is calculated and saved
"""

import math
from typing import Optional, List, Tuple
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QInputDialog, QMessageBox


class CalibrationController(QObject):
    """
    Handles 2-point calibration for calculating px_per_mm.
    
    Signals:
        calibration_complete(float): Emitted with calculated px_per_mm
        point_added(int, int): Emitted when a calibration point is clicked
        calibration_cancelled(): Emitted when calibration is cancelled
    """
    
    calibration_complete = Signal(float)
    point_added = Signal(int, int)
    calibration_cancelled = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False
        self._points: List[Tuple[int, int]] = []
        self._parent_widget = parent
    
    @property
    def is_active(self) -> bool:
        """Check if calibration mode is active."""
        return self._active
    
    @property
    def points(self) -> List[Tuple[int, int]]:
        """Get current calibration points."""
        return self._points.copy()
    
    def start(self) -> None:
        """Enter calibration mode."""
        self._active = True
        self._points = []
        print("[CALIBRATION] Mode started. Click two points on a known distance.")
    
    def cancel(self) -> None:
        """Cancel calibration mode."""
        self._active = False
        self._points = []
        self.calibration_cancelled.emit()
        print("[CALIBRATION] Mode cancelled.")
    
    def handle_click(self, x: int, y: int) -> bool:
        """
        Handle a mouse click during calibration.
        
        Args:
            x, y: Click coordinates in image space.
            
        Returns:
            True if click was consumed by calibration.
        """
        if not self._active:
            return False
        
        # Only allow 2 points max
        if len(self._points) >= 2:
            print("[CALIBRATION] Already have 2 points, ignoring additional click")
            return True
        
        self._points.append((x, y))
        self.point_added.emit(x, y)
        print(f"[CALIBRATION] Point {len(self._points)}: ({x}, {y})")
        
        if len(self._points) == 2:
            print("[CALIBRATION] Two points captured, deferring dialog...")
            # Defer dialog to next event loop cycle so click event completes first
            QTimer.singleShot(100, self._prompt_for_distance)
        
        return True
    
    def _calculate_pixel_distance(self) -> float:
        """Calculate pixel distance between the two points."""
        if len(self._points) != 2:
            return 0.0
        
        p1, p2 = self._points
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return math.sqrt(dx*dx + dy*dy)
    
    def _prompt_for_distance(self) -> None:
        """Show dialog to get known distance in mm."""
        try:
            pixel_dist = self._calculate_pixel_distance()
            print(f"[CALIBRATION] Pixel distance: {pixel_dist:.1f}")
            
            if pixel_dist < 5:
                QMessageBox.warning(
                    self._parent_widget,
                    "Calibration Error",
                    "Points are too close. Please select points further apart."
                )
                self._points = []
                return
            
            print("[CALIBRATION] Showing input dialog...")
            
            # Use getText as workaround (more reliable on some systems)
            from PySide6.QtWidgets import QInputDialog
            
            text, ok = QInputDialog.getText(
                self._parent_widget,
                "Enter Known Distance",
                f"Distance in pixels: {pixel_dist:.1f}\n\nEnter the actual distance in millimeters:",
                text="10.0"
            )
            
            print(f"[CALIBRATION] Dialog returned: ok={ok}, text='{text}'")
            
            if ok and text:
                try:
                    mm_dist = float(text)
                    if mm_dist > 0:
                        px_per_mm = pixel_dist / mm_dist
                        print(f"[CALIBRATION] Complete: {pixel_dist:.1f}px / {mm_dist:.2f}mm = {px_per_mm:.4f} px/mm")
                        
                        # Emit result and exit calibration mode
                        self._active = False
                        self._points = []
                        self.calibration_complete.emit(px_per_mm)
                        return
                except ValueError:
                    QMessageBox.warning(self._parent_widget, "Error", "Please enter a valid number")
            
            # User cancelled or invalid input, reset and allow retry
            self._points = []
            print("[CALIBRATION] Distance input cancelled. Click two points again.")
            
        except Exception as e:
            print(f"[CALIBRATION] Error in dialog: {e}")
            import traceback
            traceback.print_exc()
            self._points = []
    
    def get_overlay_data(self) -> dict:
        """
        Get data for rendering calibration overlay.
        
        Returns:
            Dict with 'points' list and 'active' status.
        """
        return {
            'active': self._active,
            'points': self._points.copy()
        }
