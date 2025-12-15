import cv2
import numpy as np
import sys
import os
import argparse
from pathlib import Path
import yaml

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from mill_presenter.core.playback import FrameLoader
from mill_presenter.core.processor import VisionProcessor
from mill_presenter.core.models import Ball
from _demo_paths import resolve_demo_video

def main():
    parser = argparse.ArgumentParser(description="Repro script for vision pipeline (prefers bundled demo video).")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Force using a tiny generated synthetic clip instead of the real demo video.",
    )
    args = parser.parse_args()

    temp_video_path: str | None = None

    if args.synthetic:
        # Create video file (mimic the test fixture)
        temp_video_path = "repro_test.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(temp_video_path, fourcc, 30.0, (100, 100))

        for _ in range(5):
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            cv2.circle(frame, (50, 50), 20, (255, 255, 255), -1)
            out.write(frame)
        out.release()

        video_path = temp_video_path
        print(f"Created synthetic clip: {video_path}")
        config = {
            "calibration": {"px_per_mm": 15.0},
            "vision": {
                "hough_param1": 50,
                "hough_param2": 30,
                "min_dist_px": 15,
                "min_circularity": 0.65,
            },
            "bins_mm": [{"label": 4, "min": 3.0, "max": 5.0}],
        }
    else:
        # Use the bundled demo clip (testing_data/DSC_3310.MOV), with fallbacks.
        video_path = str(resolve_demo_video())
        root = Path(__file__).resolve().parents[1]
        config_path = root / "configs" / "sample.config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

    # Read with FrameLoader
    loader = FrameLoader(video_path)
    print(f"Loader: {loader.width}x{loader.height}, {loader.total_frames} frames")
    
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
    if temp_video_path and os.path.exists(temp_video_path):
        os.remove(temp_video_path)

if __name__ == "__main__":
    main()
