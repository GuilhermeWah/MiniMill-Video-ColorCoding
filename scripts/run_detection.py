#!/usr/bin/env python
# MillPresenter CLI Detection Script

"""
Command-line interface for running offline detection.

Usage:
    python scripts/run_detection.py --input video.MOV --output cache.json
    python scripts/run_detection.py --input video.MOV --output cache.json --limit 100
    python scripts/run_detection.py --input video.MOV --output cache.json --visualize
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mill_presenter.core.orchestrator import ProcessorOrchestrator
from mill_presenter.core.results_cache import ResultsCache
from mill_presenter.utils import config


def progress_bar(current: int, total: int, width: int = 40) -> str:
    """Generate a progress bar string."""
    pct = current / total if total > 0 else 0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {current}/{total} ({pct*100:.1f}%)"


def run_detection(video_path: str, output_path: str, 
                  limit: int = None, drum_diameter: float = 200.0) -> bool:
    """
    Run detection pipeline on video.
    
    Args:
        video_path: Input video file.
        output_path: Output cache file.
        limit: Optional frame limit.
        drum_diameter: Drum diameter in mm.
        
    Returns:
        True if successful.
    """
    print("=" * 60)
    print("MillPresenter Detection Pipeline")
    print("=" * 60)
    print(f"Input:  {video_path}")
    print(f"Output: {output_path}")
    if limit:
        print(f"Limit:  {limit} frames")
    print(f"Drum:   {drum_diameter} mm")
    print("=" * 60)
    
    def on_progress(current, total):
        print(f"\r{progress_bar(current, total)}", end="", flush=True)
    
    orchestrator = ProcessorOrchestrator(
        video_path=video_path,
        cache_path=output_path,
        drum_diameter_mm=drum_diameter
    )
    
    success = orchestrator.run(
        progress_callback=on_progress,
        limit=limit
    )
    
    print()  # Newline after progress bar
    
    if success:
        print("\n✓ Detection complete!")
        
        # Print summary
        cache = ResultsCache(output_path)
        if cache.load():
            total_balls = sum(len(cache.get_frame(fid).balls) 
                            for fid in cache.frame_ids)
            avg_per_frame = total_balls / len(cache.frame_ids) if cache.frame_ids else 0
            
            print(f"\nSummary:")
            print(f"  Frames processed: {len(cache.frame_ids)}")
            print(f"  Total detections: {total_balls}")
            print(f"  Avg per frame:    {avg_per_frame:.1f}")
    
    return success


def visualize_result(video_path: str, cache_path: str, frame_idx: int = 0):
    """Visualize detection results on a frame."""
    import cv2
    import numpy as np
    
    from mill_presenter.core.frame_loader import FrameLoader
    from mill_presenter.core.results_cache import ResultsCache
    
    # Load cache
    cache = ResultsCache(cache_path)
    if not cache.load():
        print("Failed to load cache")
        return
    
    # Load frame
    loader = FrameLoader(video_path)
    frame = loader.get_frame(frame_idx)
    loader.close()
    
    # Get detections
    fd = cache.get_frame(frame_idx)
    if fd is None:
        print(f"No detections for frame {frame_idx}")
        return
    
    # Color map for classes
    colors = {
        4: (255, 191, 0),    # Blue (BGR)
        6: (0, 255, 0),      # Green
        8: (107, 107, 255),  # Red
        10: (0, 215, 255),   # Gold
        0: (128, 128, 128),  # Gray
    }
    
    # Draw detections
    for ball in fd.balls:
        color = colors.get(ball.cls, colors[0])
        center = (ball.x, ball.y)
        radius = int(ball.r_px)
        
        cv2.circle(frame, center, radius, color, 2)
        
        # Label
        label = f"{ball.cls}mm" if ball.cls > 0 else "?"
        cv2.putText(frame, label, (ball.x - 10, ball.y - radius - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    # Display
    print(f"\nFrame {frame_idx}: {len(fd.balls)} detections")
    print("Press any key to close...")
    
    # Resize for display
    max_dim = 1200
    h, w = frame.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
    
    cv2.imshow(f"Frame {frame_idx} - Detections", frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="MillPresenter Detection CLI")
    parser.add_argument("--input", "-i", required=True, help="Input video file")
    parser.add_argument("--output", "-o", required=True, help="Output cache file")
    parser.add_argument("--limit", "-l", type=int, default=None, help="Frame limit")
    parser.add_argument("--drum-diameter", "-d", type=float, default=200.0,
                       help="Drum diameter in mm (default: 200)")
    parser.add_argument("--visualize", "-v", action="store_true",
                       help="Visualize results after processing")
    parser.add_argument("--frame", "-f", type=int, default=0,
                       help="Frame to visualize (default: 0)")
    
    args = parser.parse_args()
    
    # Check input exists
    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}")
        return 1
    
    # Run detection
    success = run_detection(
        video_path=args.input,
        output_path=args.output,
        limit=args.limit,
        drum_diameter=args.drum_diameter
    )
    
    if not success:
        return 1
    
    # Visualize if requested
    if args.visualize:
        visualize_result(args.input, args.output, args.frame)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
