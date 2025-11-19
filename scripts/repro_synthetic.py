import cv2
import numpy as np
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from mill_presenter.core.playback import FrameLoader
from mill_presenter.core.processor import VisionProcessor
from mill_presenter.core.models import Ball

def main():
    # 1. Create video file (mimic the test fixture)
    video_path = "repro_test.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_path, fourcc, 30.0, (100, 100))
    
    for i in range(5):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # Draw a white circle (bead)
        cv2.circle(frame, (50, 50), 20, (255, 255, 255), -1)
        out.write(frame)
    out.release()
    
    print(f"Created {video_path}")

    # 2. Read back with FrameLoader
    loader = FrameLoader(video_path)
    print(f"Loader: {loader.width}x{loader.height}, {loader.total_frames} frames")

    config = {
        'calibration': {'px_per_mm': 15.0},
        'vision': {'hough_param1': 50, 'hough_param2': 30, 'min_dist_px': 15, 'min_circularity': 0.65},
        'bins_mm': [{'label': 4, 'min': 3.0, 'max': 5.0}]
    }
    
    processor = VisionProcessor(config)
    
    # 3. Process
    # We'll just process the first frame for debugging
    frame = next(loader.iter_frames())[1]
    print(f"Frame 0: shape {frame.shape}, mean={np.mean(frame)}")
    
    # Manually run pipeline steps to see where it fails
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # ... (omitted manual steps) ...
    
    # Now run the actual processor
    print("\n--- Running VisionProcessor.process_frame ---")
    balls = processor.process_frame(frame)
    print(f"Balls found: {len(balls)}")
    for b in balls:
        print(f"  {b}")

    # Cleanup
    loader.close()
    if os.path.exists(video_path):
        os.remove(video_path)

if __name__ == "__main__":
    main()
