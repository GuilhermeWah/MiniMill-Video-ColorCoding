#!/usr/bin/env python
"""
Interactive circular ROI mask creator.
Click center, then click edge to define circle.
"""
import cv2
import numpy as np
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python create_roi_circle.py <video_or_image> [output_mask.png]")
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
    
    center = None
    radius = None
    temp_pos = None
    
    def mouse_callback(event, x, y, flags, param):
        nonlocal center, radius, temp_pos
        
        # Convert to original coordinates
        orig_x = int(x / scale)
        orig_y = int(y / scale)
        
        if event == cv2.EVENT_MOUSEMOVE:
            temp_pos = (orig_x, orig_y)
        
        if event == cv2.EVENT_LBUTTONDOWN:
            if center is None:
                center = (orig_x, orig_y)
                print(f"Center set: ({orig_x}, {orig_y})")
                print("Now click on the INNER edge of the drum opening")
            else:
                # Calculate radius
                dx = orig_x - center[0]
                dy = orig_y - center[1]
                radius = int(np.sqrt(dx*dx + dy*dy))
                print(f"Radius set: {radius}px")
                print(f"Diameter: {radius*2}px")
    
    cv2.namedWindow('Circle ROI - Click center, then edge')
    cv2.setMouseCallback('Circle ROI - Click center, then edge', mouse_callback)
    
    print("\n" + "="*50)
    print("CIRCLE ROI MASK CREATOR")
    print("="*50)
    print("1. Click the CENTER of the drum opening")
    print("2. Click the INNER EDGE of the drum (radius)")
    print("")
    print("+/-: Adjust radius by 5px")
    print("Arrow keys: Move center by 5px")
    print("C: Clear and start over")
    print("S: Save mask and exit")
    print("Q/ESC: Quit without saving")
    print("="*50 + "\n")
    
    while True:
        display = display_frame.copy()
        
        # Draw current circle
        if center is not None:
            cx, cy = int(center[0] * scale), int(center[1] * scale)
            cv2.drawMarker(display, (cx, cy), (0, 255, 0), cv2.MARKER_CROSS, 20, 2)
            
            if radius is not None:
                r_scaled = int(radius * scale)
                cv2.circle(display, (cx, cy), r_scaled, (0, 255, 0), 2)
            elif temp_pos is not None:
                # Preview radius while moving mouse
                dx = temp_pos[0] - center[0]
                dy = temp_pos[1] - center[1]
                r_preview = int(np.sqrt(dx*dx + dy*dy) * scale)
                cv2.circle(display, (cx, cy), r_preview, (0, 255, 255), 1)
        
        # Status text
        status = "Click CENTER" if center is None else ("Click EDGE" if radius is None else f"R={radius}px | S=Save")
        cv2.putText(display, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow('Circle ROI - Click center, then edge', display)
        
        key = cv2.waitKey(30) & 0xFF
        if key == ord('q') or key == 27:
            print("Cancelled")
            break
        elif key == ord('c'):
            center = None
            radius = None
            print("Cleared")
        elif key == ord('+') or key == ord('='):
            if radius is not None:
                radius += 5
                print(f"Radius: {radius}px")
        elif key == ord('-') or key == ord('_'):
            if radius is not None and radius > 10:
                radius -= 5
                print(f"Radius: {radius}px")
        elif key == 82:  # Up arrow
            if center is not None:
                center = (center[0], center[1] - 5)
                print(f"Center: {center}")
        elif key == 84:  # Down arrow
            if center is not None:
                center = (center[0], center[1] + 5)
                print(f"Center: {center}")
        elif key == 81:  # Left arrow
            if center is not None:
                center = (center[0] - 5, center[1])
                print(f"Center: {center}")
        elif key == 83:  # Right arrow
            if center is not None:
                center = (center[0] + 5, center[1])
                print(f"Center: {center}")
        elif key == ord('s') and center is not None and radius is not None:
            # Create circular mask
            mask = np.zeros((orig_h, orig_w), dtype=np.uint8)
            cv2.circle(mask, center, radius, 255, -1)  # Filled circle
            
            # Save
            cv2.imwrite(output, mask)
            print(f"\nMask saved to: {output}")
            print(f"Center: {center}, Radius: {radius}px")
            print(f"White pixels: {np.sum(mask > 0)} ({100*np.sum(mask > 0)/mask.size:.1f}%)")
            break
    
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
