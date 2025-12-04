import cv2
import numpy as np
from typing import List, Tuple, Optional
from mill_presenter.core.models import Ball
from mill_presenter.utils.logging import get_logger

logger = get_logger(__name__)

class VisionProcessor:
    """
    The Core Vision Pipeline.
    Responsibility: Turn a raw BGR frame into a list of Ball objects.
    """
    def __init__(self, config: dict):
        self.config = config
        self.px_per_mm = config.get('calibration', {}).get('px_per_mm', 1.0)
        if not self.px_per_mm:
            self.px_per_mm = 1.0 # Fallback to avoid div/0
            
        # Vision Parameters
        self.hough_p1 = config.get('vision', {}).get('hough_param1', 50)
        self.hough_p2 = config.get('vision', {}).get('hough_param2', 20) # Lowered from 30 to catch more balls
        self.min_dist = config.get('vision', {}).get('min_dist_px', 15)
        self.contour_min_circularity = config.get('vision', {}).get('min_circularity', 0.65) # Lowered from 0.75 for glare tolerance
        
        # Bin definitions
        self.bins = config.get('bins_mm', [])

    def process_frame(self, frame_bgr: np.ndarray, roi_mask: Optional[np.ndarray] = None) -> List[Ball]:
        """
        Main pipeline entry point.
        1. Preprocess (Gray -> Bilateral -> CLAHE)
        2. Detect (Hough + Contours)
        3. Filter (ROI + Annulus Logic)
        4. Classify (px -> mm)
        """
        # 1. Preprocessing
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        
        # Bilateral Filter: Smooth noise/glare but keep edges sharp
        # d=9, sigmaColor=75, sigmaSpace=75 are standard starting points
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # CLAHE: Boost local contrast to see beads in shadows
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(filtered)
        
        # 2. Detection - Path A: Hough Circles (The "Pile" Detector)
        # minRadius/maxRadius should be derived from bins if possible, 
        # but for now we use safe wide defaults or config
        circles = cv2.HoughCircles(
            enhanced, 
            cv2.HOUGH_GRADIENT, 
            dp=1, 
            minDist=self.min_dist,
            param1=self.hough_p1,
            param2=self.hough_p2,
            minRadius=4, # Lowered to catch small beads (4mm ~ 11px dia -> 5.5px rad)
            maxRadius=30 # Lowered to avoid detecting drum features (10mm ~ 29px dia -> 14.5px rad)
        )
        
        candidates = []
        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                x, y, r = int(i[0]), int(i[1]), float(i[2])
                candidates.append((x, y, r, 0.8)) # 0.8 is arbitrary confidence for Hough

        # Path B: Contours (The "Flyer" Detector)
        # 1. Canny Edge Detection
        # Use Otsu's thresholding to find optimal Canny parameters automatically
        high_thresh, _ = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        low_thresh = 0.5 * high_thresh
        edges = cv2.Canny(enhanced, low_thresh, high_thresh)
        
        # 2. Morphology to close gaps in edges
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        closed_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        # 3. Find Contours
        contours, _ = cv2.findContours(closed_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            # Filter by Area (ignore tiny noise)
            area = cv2.contourArea(cnt)
            if area < 50: # Minimum area threshold
                continue
                
            # Filter by Circularity
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0: continue
            circularity = 4 * np.pi * area / (perimeter * perimeter)
            
            if circularity > self.contour_min_circularity: # Only reasonably circular objects
                # Fit circle
                (x, y), r = cv2.minEnclosingCircle(cnt)
                candidates.append((int(x), int(y), float(r), 0.6 * circularity)) # Conf based on circularity
            else:
                # Debug
                # print(f"Rejected contour area={area} circ={circularity}")
                pass

        # 3. Filtering & Annulus Logic
        # Sort candidates by radius (descending) to handle annulus logic
        # We want to process large circles first to identify them as "parents" of smaller holes
        candidates.sort(key=lambda c: c[2], reverse=True)
        
        final_candidates = []
        
        for i, (x, y, r, conf) in enumerate(candidates):
            # ROI Check
            if roi_mask is not None:
                # Check if center is within white area of mask
                if not (0 <= y < roi_mask.shape[0] and 0 <= x < roi_mask.shape[1]):
                    continue
                if roi_mask[y, x] == 0:
                    continue

            # Brightness Filter (Reject Dark Holes)
            # Check the brightness of the center pixel in the original grayscale image
            # Beads are shiny/bright. Holes are dark/shadowy.
            # We check a small 3x3 area at the center to be robust against noise
            if 0 <= y < gray.shape[0] and 0 <= x < gray.shape[1]:
                # Get a small patch
                y1, y2 = max(0, y-2), min(gray.shape[0], y+3)
                x1, x2 = max(0, x-2), min(gray.shape[1], x+3)
                center_patch = gray[y1:y2, x1:x2]
                avg_brightness = np.mean(center_patch)
                
                # Threshold: If center is very dark, it's likely a hole or background
                # Adjust this threshold based on your lighting. 
                # 50 is a conservative guess for "dark shadow".
                if avg_brightness < 50: 
                    # logger.debug(f"Rejected dark candidate at {x},{y} brightness={avg_brightness}")
                    continue

            # Annulus Logic: Check if this circle is a hole inside a previously accepted larger circle
            is_hole = False
            for (fx, fy, fr, fconf) in final_candidates:
                # Distance between centers
                dist = np.sqrt((x - fx)**2 + (y - fy)**2)
                
                # If center is inside the other circle AND radius is significantly smaller
                # We are iterating sorted by radius (descending), so 'fr' is always >= 'r'
                if dist < (fr * 0.5) and r < (fr * 0.8):
                    is_hole = True
                    break
            
            if is_hole:
                continue
                
            # NMS (Non-Maximum Suppression) - Simple version
            # If this circle overlaps significantly with an existing one of similar size, skip it
            is_duplicate = False
            for (fx, fy, fr, fconf) in final_candidates:
                dist = np.sqrt((x - fx)**2 + (y - fy)**2)
                # If overlap is > 50% of radius
                if dist < (fr * 0.5) and abs(r - fr) < (fr * 0.3):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                final_candidates.append((x, y, r, conf))

        # 4. Classification
        valid_balls = []
        for (x, y, r, conf) in final_candidates:
            diameter_mm = (2 * r) / self.px_per_mm
            cls = self._classify_diameter(diameter_mm)
            
            if cls is not None:
                valid_balls.append(Ball(x, y, r, diameter_mm, cls, conf))
            else:
                print(f"DEBUG: Ball at ({x},{y}) r={r} d_mm={diameter_mm:.2f} not in any bin. Bins: {self.bins}")
                
        return valid_balls

    def _classify_diameter(self, d_mm: float) -> Optional[int]:
        """Maps a diameter in mm to a class label (4, 6, 8, 10)."""
        for bin_def in self.bins:
            if bin_def['min'] <= d_mm < bin_def['max']:
                return bin_def['label']
        return None
