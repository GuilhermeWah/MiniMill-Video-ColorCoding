#!/usr/bin/env python
"""
Interactive ROI mask creator.
Draw a polygon to define the valid detection region.
"""
import cv2
import numpy as np
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python create_roi_mask.py <video_or_image> [output_mask.png]")
        sys.exit(1)
    
    path = Path(sys.argv[1])
    output = sys.argv[2] if len(sys.argv) > 2 else "content/roi_mask.png"
    
    # Load frame
    if path.suffix.lower() in ['.mov', '.mp4', '.avi']:
        cap = cv2.VideoCapture(str(path))
        ret, frame = cap.read()
        cap.release()
    else:
        frame = cv2.imread(str(path))
    
    if frame is None:
        print("Failed to load image/video")
        sys.exit(1)
    
    orig_h, orig_w = frame.shape[:2]
    
    # Scale for display
    scale = 1.0
    if max(orig_h, orig_w) > 1200:
        scale = 1200 / max(orig_h, orig_w)
        display_frame = cv2.resize(frame, None, fx=scale, fy=scale)
    else:
        display_frame = frame.copy()
    
    points = []
    
    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # Convert to original coordinates
            orig_x = int(x / scale)
            orig_y = int(y / scale)
            points.append((orig_x, orig_y))
            print(f"Point {len(points)}: ({orig_x}, {orig_y})")
    
    cv2.namedWindow('Draw ROI - Click to add points')
    cv2.setMouseCallback('Draw ROI - Click to add points', mouse_callback)
    
    print("\n" + "="*50)
    print("ROI MASK CREATOR")
    print("="*50)
    print("Left-click: Add polygon point")
    print("C: Clear all points")
    print("S: Save mask and exit")
    print("Q/ESC: Quit without saving")
    print("="*50 + "\n")
    
    while True:
        display = display_frame.copy()
        
        # Draw existing points and lines
        if len(points) > 0:
            # Draw points
            for i, (ox, oy) in enumerate(points):
                sx, sy = int(ox * scale), int(oy * scale)
                cv2.circle(display, (sx, sy), 5, (0, 255, 0), -1)
                cv2.putText(display, str(i+1), (sx+10, sy), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Draw lines between points
            for i in range(len(points) - 1):
                p1 = (int(points[i][0] * scale), int(points[i][1] * scale))
                p2 = (int(points[i+1][0] * scale), int(points[i+1][1] * scale))
                cv2.line(display, p1, p2, (0, 255, 0), 2)
            
            # Draw closing line (polygon preview)
            if len(points) > 2:
                p1 = (int(points[-1][0] * scale), int(points[-1][1] * scale))
                p2 = (int(points[0][0] * scale), int(points[0][1] * scale))
                cv2.line(display, p1, p2, (0, 255, 0), 1)  # Dotted preview
        
        cv2.putText(display, f"Points: {len(points)} | S=Save, C=Clear, Q=Quit", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow('Draw ROI - Click to add points', display)
        
        key = cv2.waitKey(30) & 0xFF
        if key == ord('q') or key == 27:
            print("Cancelled")
            break
        elif key == ord('c'):
            points = []
            print("Points cleared")
        elif key == ord('s') and len(points) >= 3:
            # Create mask
            mask = np.zeros((orig_h, orig_w), dtype=np.uint8)
            pts = np.array(points, dtype=np.int32)
            cv2.fillPoly(mask, [pts], 255)
            
            # Save
            cv2.imwrite(output, mask)
            print(f"\nMask saved to: {output}")
            print(f"White pixels: {np.sum(mask > 0)} ({100*np.sum(mask > 0)/mask.size:.1f}%)")
            break
    
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
