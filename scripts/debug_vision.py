import cv2
import numpy as np
import sys
import os
import yaml

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from mill_presenter.core.playback import FrameLoader
from mill_presenter.core.processor import VisionProcessor

def create_test_video(path):
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(path, fourcc, 30.0, (100, 100))
    for i in range(5):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.circle(frame, (50, 50), 20, (255, 255, 255), -1)
        out.write(frame)
    out.release()

def main():
    # Use relative paths to avoid encoding issues with "Área de Trabalho"
    video_path = "content/DSC_3310.MOV"
    roi_path = "content/roi_mask.png"
    
    if not os.path.exists(video_path):
        print(f"Error: Video not found at {video_path}")
        return

    loader = FrameLoader(video_path)
    print(f"Loader: {loader.width}x{loader.height}, {loader.total_frames} frames, {loader.fps} fps")
    
    # Load ROI if available
    roi_mask = None
    if os.path.exists(roi_path):
        roi_mask = cv2.imread(roi_path, cv2.IMREAD_GRAYSCALE)
        print(f"Loaded ROI mask: {roi_mask.shape}")
    
    config = {
        'calibration': {'px_per_mm': 10.0}, # Placeholder calibration
        'vision': {'hough_param1': 50, 'hough_param2': 30, 'min_dist_px': 15},
        'bins_mm': [
            {'label': 4, 'min': 3.0, 'max': 5.0},
            {'label': 6, 'min': 5.0, 'max': 7.0},
            {'label': 8, 'min': 7.0, 'max': 9.0},
            {'label': 10, 'min': 9.0, 'max': 11.0}
        ]
    }
    
    processor = VisionProcessor(config)
    
    # Process first 10 frames only
    for i, frame in loader.iter_frames():
        if i >= 10: break
        
        print(f"Frame {i}: shape {frame.shape}")
        balls = processor.process_frame(frame, roi_mask=roi_mask)
        print(f"  Balls: {len(balls)}")
        if len(balls) > 0:
            print(f"    First 3 balls: {balls[:3]}")

    loader.close()

if __name__ == "__main__":
    main()
