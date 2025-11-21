import math
from typing import Tuple

def calculate_px_per_mm(p1: Tuple[float, float], p2: Tuple[float, float], known_mm: float) -> float:
    """
    Calculates pixels per millimeter based on two points and a known distance.
    """
    if known_mm <= 0:
        raise ValueError("Known distance must be positive")
        
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dist_px = math.sqrt(dx*dx + dy*dy)
    
    if dist_px == 0:
        raise ValueError("Points cannot be identical")
        
    return dist_px / known_mm
