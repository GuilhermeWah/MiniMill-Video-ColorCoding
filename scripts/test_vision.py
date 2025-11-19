import sys
import os
import cv2
import yaml
import numpy as np

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from mill_presenter.core.playback import FrameLoader
from mill_presenter.core.processor import VisionProcessor
from mill_presenter.utils.logging import setup_logging

def main():
    setup_logging()
    
    # 1. Load Config
    config_path = os.path.join(os.path.dirname(__file__), '../configs/sample.config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        
    # HACK: Set a dummy px_per_mm for testing if it's null in config
    if not config['calibration']['px_per_mm']:
        print("⚠️  No calibration found. Using dummy value (10.0 px/mm) for testing.")
        config['calibration']['px_per_mm'] = 10.0

    # 2. Load Video
    video_path = os.path.join(os.path.dirname(__file__), '../content/DSC_3310.MOV')
    if not os.path.exists(video_path):
        print(f"❌ Video not found at: {video_path}")
        return

    print(f"Loading video: {video_path}")
    loader = FrameLoader(video_path)
    
    # 3. Initialize Processor
    processor = VisionProcessor(config)
    
    # 3b. Load ROI Mask
    roi_mask_path = os.path.join(os.path.dirname(__file__), '../content/roi_mask.png')
    roi_mask = None
    if os.path.exists(roi_mask_path):
        try:
            with open(roi_mask_path, 'rb') as f:
                file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
                roi_mask = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
            print(f"✅ Loaded ROI mask: {roi_mask.shape}")
        except Exception as e:
            print(f"⚠️  Failed to load ROI mask: {e}")
    else:
        print(f"⚠️  No ROI mask found at {roi_mask_path}")
    
    # 4. Process a specific frame (e.g., frame 100 where beads are settled)
    target_frame = 100
    print(f"Seeking to frame {target_frame}...")
    
    # Simple seek loop
    frame_img = None
    for idx, img in loader.iter_frames(start_frame=target_frame):
        if idx == target_frame:
            frame_img = img
            break
            
    if frame_img is None:
        print("❌ Failed to load frame.")
        return

    print("Processing frame...")
    balls = processor.process_frame(frame_img, roi_mask=roi_mask)
    print(f"✅ Detected {len(balls)} beads.")
    
    # 5. Draw Results
    output_img = frame_img.copy()
    for ball in balls:
        # Draw outer circle
        cv2.circle(output_img, (ball.x, ball.y), int(ball.r_px), (0, 255, 0), 2)
        # Draw center
        cv2.circle(output_img, (ball.x, ball.y), 2, (0, 0, 255), -1)
        # Draw class label
        cv2.putText(output_img, f"{ball.cls}mm", (ball.x - 10, ball.y - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # 6. Save Output
    exports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../exports'))
    os.makedirs(exports_dir, exist_ok=True)
    output_path = os.path.join(exports_dir, 'debug_vision_test.jpg')

    # OpenCV on Windows has issues with Unicode paths - use imencode workaround
    is_success, buffer = cv2.imencode('.jpg', output_img)
    if is_success:
        with open(output_path, 'wb') as f:
            f.write(buffer)
        print(f"✅ Saved debug image to: {output_path}")
    else:
        print(f"❌ Failed to encode image.")
    
    loader.close()

if __name__ == "__main__":
    main()
