from typing import List, Tuple, Optional
from mill_presenter.core.calibration import calculate_px_per_mm

class CalibrationController:
    def __init__(self, widget, config: dict):
        self.widget = widget
        self.config = config
        self.is_active = False
        self.points: List[Tuple[float, float]] = []
        self.known_distance_mm: float = 0.0

    def start(self):
        self.is_active = True
        self.points = []
        # Tell widget to listen for clicks
        if hasattr(self.widget, 'set_interaction_mode'):
            self.widget.set_interaction_mode('calibration')

    def cancel(self):
        self.is_active = False
        self.points = []
        if hasattr(self.widget, 'set_interaction_mode'):
            self.widget.set_interaction_mode('none')

    def handle_click(self, x: float, y: float):
        if not self.is_active:
            return
        
        # For 2-point calibration, we reset if we already have 2 points
        if len(self.points) >= 2:
            self.points = []
            
        self.points.append((x, y))
        
        # Update widget visualization
        if hasattr(self.widget, 'set_calibration_points'):
            self.widget.set_calibration_points(self.points)

    def set_known_distance(self, mm: float):
        self.known_distance_mm = mm

    def apply(self):
        if len(self.points) != 2 or self.known_distance_mm <= 0:
            return
            
        ratio = calculate_px_per_mm(self.points[0], self.points[1], self.known_distance_mm)
        
        # Update config
        if 'calibration' not in self.config:
            self.config['calibration'] = {}
        self.config['calibration']['px_per_mm'] = ratio
        
        self.cancel()
