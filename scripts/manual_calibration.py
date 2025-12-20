#!/usr/bin/env python3
"""
Manual Two-Point Calibration Tool

Interactive tool for manually calibrating px_per_mm by clicking two points
on a known physical dimension (e.g., drum diameter).

Usage:
    python scripts/manual_calibration.py --video path/to/video.mov

Instructions:
1. Click the first point on the drum edge
2. Click the second point on the opposite drum edge
3. Enter the known distance in mm (e.g., 200 for drum diameter)
4. Tool calculates and displays px_per_mm
"""

import argparse
import sys
from pathlib import Path
import cv2
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mill_presenter.core.frame_loader import FrameLoader


class TwoPointCalibrator:
    """Interactive two-point calibration tool."""
    
    def __init__(self, frame: np.ndarray):
        self.frame = frame.copy()
        self.display = frame.copy()
        self.points = []
        self.px_per_mm = None
        self.distance_px = None
        
    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse events."""
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.points) < 2:
                self.points.append((x, y))
                self._redraw()
                
                if len(self.points) == 2:
                    self._calculate_distance()
    
    def _redraw(self):
        """Redraw display with points and line."""
        self.display = self.frame.copy()
        
        # Draw points
        for i, pt in enumerate(self.points):
            color = (0, 255, 0) if i == 0 else (0, 0, 255)
            cv2.circle(self.display, pt, 8, color, -1)
            cv2.circle(self.display, pt, 10, (255, 255, 255), 2)
            label = f"P{i+1}: ({pt[0]}, {pt[1]})"
            cv2.putText(self.display, label, (pt[0] + 15, pt[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Draw line between points
        if len(self.points) == 2:
            cv2.line(self.display, self.points[0], self.points[1], 
                    (255, 255, 0), 2)
        
        # Draw instructions
        if len(self.points) == 0:
            text = "Click FIRST point on drum edge"
        elif len(self.points) == 1:
            text = "Click SECOND point on opposite drum edge"
        else:
            text = f"Distance: {self.distance_px:.1f} pixels | Press ENTER to confirm, R to reset"
        
        cv2.putText(self.display, text, (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    
    def _calculate_distance(self):
        """Calculate pixel distance between points."""
        p1, p2 = self.points
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        self.distance_px = np.sqrt(dx*dx + dy*dy)
    
    def run(self) -> tuple:
        """
        Run interactive calibration.
        
        Returns:
            (px_per_mm, distance_px, distance_mm) or None if cancelled
        """
        window_name = "Two-Point Calibration (Q=quit, R=reset, ENTER=confirm)"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(window_name, self.mouse_callback)
        
        self._redraw()
        
        while True:
            cv2.imshow(window_name, self.display)
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == 27:  # Q or Escape
                cv2.destroyAllWindows()
                return None
            
            elif key == ord('r'):  # Reset
                self.points = []
                self.distance_px = None
                self._redraw()
            
            elif key == 13 and len(self.points) == 2:  # Enter
                cv2.destroyAllWindows()
                
                # Get physical distance from user
                print(f"\nPixel distance: {self.distance_px:.2f} px")
                try:
                    distance_mm = float(input("Enter physical distance in mm: "))
                except ValueError:
                    print("Invalid input. Using default drum diameter of 200mm.")
                    distance_mm = 200.0
                
                self.px_per_mm = self.distance_px / distance_mm
                
                return (self.px_per_mm, self.distance_px, distance_mm)
        
        return None


def calibrate_video(video_path: str, frame_idx: int = 0, output_file: str = None):
    """
    Run calibration on a video frame.
    
    Args:
        video_path: Path to video file
        frame_idx: Frame index to use for calibration
        output_file: Optional JSON file to save calibration
    """
    print(f"Loading video: {video_path}")
    loader = FrameLoader(video_path)
    
    print(f"Video: {loader.width}x{loader.height}, {loader.total_frames} frames")
    
    frame = loader.get_frame(frame_idx)
    loader.close()
    
    print("\n=== Two-Point Calibration ===")
    print("Click two points on the drum edge (opposite sides)")
    print("Keys: R=reset, ENTER=confirm, Q=quit")
    
    calibrator = TwoPointCalibrator(frame)
    result = calibrator.run()
    
    if result:
        px_per_mm, distance_px, distance_mm = result
        
        print("\n=== Calibration Result ===")
        print(f"  Pixel distance: {distance_px:.2f} px")
        print(f"  Physical distance: {distance_mm:.2f} mm")
        print(f"  Calibration: {px_per_mm:.4f} px/mm")
        
        # Calculate expected bead sizes
        print("\n  Expected bead radii (in pixels):")
        for size_mm in [4, 6, 8, 10]:
            r_px = (size_mm / 2) * px_per_mm
            print(f"    {size_mm}mm bead: {r_px:.1f} px radius")
        
        if output_file:
            import json
            calibration_data = {
                "video": str(Path(video_path).name),
                "px_per_mm": px_per_mm,
                "distance_px": distance_px,
                "distance_mm": distance_mm,
                "points": calibrator.points
            }
            with open(output_file, 'w') as f:
                json.dump(calibration_data, f, indent=2)
            print(f"\n  Saved calibration to: {output_file}")
        
        return px_per_mm
    else:
        print("\nCalibration cancelled.")
        return None


def main():
    parser = argparse.ArgumentParser(description="Manual two-point calibration tool")
    parser.add_argument("--video", "-v", required=True, help="Path to input video")
    parser.add_argument("--frame", "-f", type=int, default=0, help="Frame index to use")
    parser.add_argument("--output", "-o", help="Output JSON file for calibration data")
    
    args = parser.parse_args()
    
    calibrate_video(
        video_path=args.video,
        frame_idx=args.frame,
        output_file=args.output
    )


if __name__ == "__main__":
    main()
