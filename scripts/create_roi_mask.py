"""
Create ROI mask to exclude frame/bolts from detection.
This masks out everything except the circular mill drum area.
"""
import cv2
import numpy as np
import os

def main():
    # Load the debug image to get dimensions
    debug_img_path = os.path.join(os.path.dirname(__file__), '../exports/debug_vision_test.jpg')
    
    # Use imread workaround for Unicode paths
    try:
        with open(debug_img_path, 'rb') as f:
            file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"❌ Could not load debug image from {debug_img_path}: {e}")
        return
    
    if img is None:
        print(f"❌ Could not decode debug image")
        return
    
    h, w = img.shape[:2]
    print(f"Image dimensions: {w}x{h}")
    
    # Create black mask
    mask = np.zeros((h, w), dtype=np.uint8)
    
    # Define the circular mill drum region (estimated from the image)
    # The mill appears to be centered with a large circular region
    center_x = w // 2
    center_y = h // 2
    
    # Main mill drum radius (estimate - adjust if needed)
    # Looking at the image, the drum takes up most of the frame
    drum_radius = int(min(w, h) * 0.45)  # ~45% of frame dimension
    
    # Draw white circle for valid region
    cv2.circle(mask, (center_x, center_y), drum_radius, 255, -1)
    
    # Optionally, create a smaller inner exclusion (if there's a center bolt/shaft)
    # Uncomment if needed:
    # center_exclusion_radius = 50
    # cv2.circle(mask, (center_x, center_y), center_exclusion_radius, 0, -1)
    
    # Save mask
    mask_path = os.path.join(os.path.dirname(__file__), '../content/roi_mask.png')
    
    # Use imencode workaround for Unicode paths
    is_success, buffer = cv2.imencode('.png', mask)
    if is_success:
        with open(mask_path, 'wb') as f:
            f.write(buffer)
        print(f"✅ ROI mask saved to: {mask_path}")
        print(f"   Center: ({center_x}, {center_y}), Radius: {drum_radius}px")
    else:
        print("❌ Failed to encode mask")
    
    # Save a preview showing the mask overlay
    preview = cv2.addWeighted(img, 0.7, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR), 0.3, 0)
    preview_path = os.path.join(os.path.dirname(__file__), '../exports/roi_preview.jpg')
    is_success, buffer = cv2.imencode('.jpg', preview)
    if is_success:
        with open(preview_path, 'wb') as f:
            f.write(buffer)
        print(f"✅ ROI preview saved to: {preview_path}")

if __name__ == "__main__":
    main()
