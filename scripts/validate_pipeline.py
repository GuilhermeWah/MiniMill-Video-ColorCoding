#!/usr/bin/env python3
"""
Pipeline Validation Script

Generates side-by-side comparison images for each pipeline stage:
- Right side: Original frame (no overlays)
- Left side: Processed frame with stage output
- Cropped to ROI (drum area only)

Usage:
    python scripts/validate_pipeline.py --video path/to/video.mov --output output_dir
"""

import argparse
import sys
from pathlib import Path
import cv2
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mill_presenter.core.frame_loader import FrameLoader
from mill_presenter.core.drum_geometry import DrumGeometry
from mill_presenter.core.preprocessor import Preprocessor
from mill_presenter.core.vision_processor import VisionProcessor
from mill_presenter.core.confidence_scorer import ConfidenceScorer
from mill_presenter.core.detection_filter import DetectionFilter
from mill_presenter.core.classifier import Classifier


# Color scheme for size classes (BGR)
CLASS_COLORS = {
    4: (255, 191, 0),    # Deep Sky Blue
    6: (0, 255, 0),      # Green
    8: (107, 107, 255),  # Coral Red
    10: (0, 215, 255),   # Gold
    0: (128, 128, 128),  # Gray (unknown)
}


def crop_to_roi(image: np.ndarray, geometry: DrumGeometry, padding: int = 20) -> np.ndarray:
    """Crop image to drum ROI with padding."""
    cx, cy = geometry.center
    r = geometry.radius + padding
    
    h, w = image.shape[:2]
    x1 = max(0, cx - r)
    y1 = max(0, cy - r)
    x2 = min(w, cx + r)
    y2 = min(h, cy + r)
    
    return image[y1:y2, x1:x2]


def create_side_by_side(left: np.ndarray, right: np.ndarray, 
                        left_label: str = "Processed", 
                        right_label: str = "Original") -> np.ndarray:
    """Create side-by-side comparison image."""
    # Ensure same dimensions
    h1, w1 = left.shape[:2]
    h2, w2 = right.shape[:2]
    h = max(h1, h2)
    w = max(w1, w2)
    
    # Ensure 3-channel
    if len(left.shape) == 2:
        left = cv2.cvtColor(left, cv2.COLOR_GRAY2BGR)
    if len(right.shape) == 2:
        right = cv2.cvtColor(right, cv2.COLOR_GRAY2BGR)
    
    # Resize if needed
    if left.shape[:2] != (h, w):
        left = cv2.resize(left, (w, h))
    if right.shape[:2] != (h, w):
        right = cv2.resize(right, (w, h))
    
    # Combine horizontally
    combined = np.hstack([left, right])
    
    # Add labels
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(combined, left_label, (10, 30), font, 1, (255, 255, 255), 2)
    cv2.putText(combined, right_label, (w + 10, 30), font, 1, (255, 255, 255), 2)
    
    # Add divider line
    cv2.line(combined, (w, 0), (w, h), (255, 255, 255), 2)
    
    return combined


def draw_detections(frame: np.ndarray, detections: list, 
                    with_labels: bool = True) -> np.ndarray:
    """Draw detection circles on frame."""
    output = frame.copy()
    if len(output.shape) == 2:
        output = cv2.cvtColor(output, cv2.COLOR_GRAY2BGR)
    
    for det in detections:
        # Handle both dataclass objects and dicts
        if hasattr(det, 'x'):
            x = int(det.x)
            y = int(det.y)
            r = int(det.r_px)
            cls = getattr(det, 'cls', 0)
            conf = getattr(det, 'conf', 0)
        else:
            x = int(det.get('x', 0))
            y = int(det.get('y', 0))
            r = int(det.get('r_px', 10))
            cls = det.get('cls', 0)
            conf = det.get('conf', 0)
        
        color = CLASS_COLORS.get(cls, (128, 128, 128))
        cv2.circle(output, (x, y), r, color, 2)
        
        if with_labels and conf:
            label = f"{conf:.2f}"
            cv2.putText(output, label, (x - 15, y - r - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    return output


def draw_drum_geometry(frame: np.ndarray, geometry: DrumGeometry) -> np.ndarray:
    """Draw drum geometry overlay."""
    output = frame.copy()
    if len(output.shape) == 2:
        output = cv2.cvtColor(output, cv2.COLOR_GRAY2BGR)
    
    # Draw drum circle
    cv2.circle(output, geometry.center, geometry.radius, (0, 255, 255), 3)
    
    # Draw center cross
    cx, cy = geometry.center
    cv2.line(output, (cx - 20, cy), (cx + 20, cy), (0, 255, 255), 2)
    cv2.line(output, (cx, cy - 20), (cx, cy + 20), (0, 255, 255), 2)
    
    # Add calibration info
    info = f"r={geometry.radius}px, {geometry.px_per_mm:.2f} px/mm"
    cv2.putText(output, info, (cx - 100, cy + geometry.radius + 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    
    return output


def validate_pipeline(video_path: str, output_dir: str, 
                      frame_indices: list = None, 
                      drum_diameter_mm: float = 200.0):
    """Run full pipeline validation and generate comparison images."""
    
    # Create structured output directory
    video_name = Path(video_path).stem
    base_path = Path(output_dir) / video_name
    
    # Create stage subdirectories
    stage_dirs = {
        1: base_path / "01_drum_geometry",
        2: base_path / "02_preprocessing", 
        3: base_path / "03_detection",
        4: base_path / "04_scoring",
        5: base_path / "05_filtering",
        6: base_path / "06_classification",
    }
    
    for stage_dir in stage_dirs.values():
        stage_dir.mkdir(parents=True, exist_ok=True)
    
    if frame_indices is None:
        frame_indices = [0, 50, 100]
    
    print(f"Loading video: {video_path}")
    loader = FrameLoader(video_path)
    
    print(f"Video: {loader.width}x{loader.height}, {loader.total_frames} frames, {loader.fps:.1f} fps")
    print(f"Output: {base_path}")
    
    # Get first frame for geometry detection
    first_frame = loader.get_frame(0)
    
    # Stage 1: Drum Geometry Detection
    print("\n=== Stage 1: Drum Geometry Detection ===")
    geometry = DrumGeometry.detect(first_frame, drum_diameter_mm)
    print(f"  Center: {geometry.center}")
    print(f"  Radius: {geometry.radius} px")
    print(f"  Calibration: {geometry.px_per_mm:.3f} px/mm")
    
    # Generate geometry comparison
    geometry_viz = draw_drum_geometry(first_frame, geometry)
    geometry_cropped = crop_to_roi(geometry_viz, geometry)
    original_cropped = crop_to_roi(first_frame, geometry)
    comparison = create_side_by_side(geometry_cropped, original_cropped, 
                                     "Drum Detection", "Original")
    cv2.imwrite(str(stage_dirs[1] / "drum_detection.png"), comparison)
    print(f"  Saved: 01_drum_geometry/drum_detection.png")
    
    # Save calibration info
    with open(stage_dirs[1] / "calibration.txt", 'w') as f:
        f.write(f"Video: {video_name}\n")
        f.write(f"Center: {geometry.center}\n")
        f.write(f"Radius: {geometry.radius} px\n")
        f.write(f"px_per_mm: {geometry.px_per_mm:.4f}\n")
        f.write(f"Drum diameter: {drum_diameter_mm} mm\n")
    
    # Initialize processors
    preprocessor = Preprocessor()
    vision_processor = VisionProcessor()
    scorer = ConfidenceScorer()
    filter_ = DetectionFilter()
    classifier = Classifier()
    
    # Generate ROI mask
    roi_mask = geometry.get_roi_mask((loader.height, loader.width))
    
    # Summary stats
    summary = {
        "video": video_name,
        "frames_processed": [],
        "calibration": {"px_per_mm": geometry.px_per_mm}
    }
    
    for frame_idx in frame_indices:
        if frame_idx >= loader.total_frames:
            continue
            
        print(f"\n=== Processing Frame {frame_idx} ===")
        frame_bgr = loader.get_frame(frame_idx)
        original_cropped = crop_to_roi(frame_bgr, geometry)
        
        frame_stats = {"frame": frame_idx}
        
        # Stage 2: Preprocessing
        print("  Stage 2: Preprocessing...")
        preprocessed = preprocessor.process(frame_bgr, roi_mask)
        preprocessed_cropped = crop_to_roi(preprocessed, geometry)
        comparison = create_side_by_side(preprocessed_cropped, original_cropped,
                                        "Preprocessed", "Original")
        cv2.imwrite(str(stage_dirs[2] / f"frame_{frame_idx:04d}.png"), comparison)
        
        # Stage 3: Circle Detection
        print("  Stage 3: Circle Detection...")
        raw_detections = vision_processor.detect(preprocessed, geometry)
        frame_stats["raw_candidates"] = len(raw_detections)
        print(f"    Raw candidates: {len(raw_detections)}")
        
        detection_viz = draw_detections(frame_bgr, raw_detections, with_labels=False)
        detection_cropped = crop_to_roi(detection_viz, geometry)
        comparison = create_side_by_side(detection_cropped, original_cropped,
                                        f"Detections ({len(raw_detections)})", "Original")
        cv2.imwrite(str(stage_dirs[3] / f"frame_{frame_idx:04d}.png"), comparison)
        
        # Stage 4: Confidence Scoring
        print("  Stage 4: Confidence Scoring...")
        scored = scorer.score(raw_detections, preprocessed, geometry)
        avg_conf = sum(d.conf for d in scored) / len(scored) if scored else 0
        frame_stats["avg_confidence"] = round(avg_conf, 3)
        print(f"    Scored: {len(scored)}, avg confidence: {avg_conf:.3f}")
        
        scored_viz = draw_detections(frame_bgr, scored, with_labels=True)
        scored_cropped = crop_to_roi(scored_viz, geometry)
        comparison = create_side_by_side(scored_cropped, original_cropped,
                                        f"Scored (avg={avg_conf:.2f})", "Original")
        cv2.imwrite(str(stage_dirs[4] / f"frame_{frame_idx:04d}.png"), comparison)
        
        # Stage 5: Filtering
        print("  Stage 5: Filtering...")
        filtered = filter_.filter(scored, geometry, preprocessed)
        frame_stats["after_filtering"] = len(filtered)
        print(f"    After filtering: {len(filtered)}")
        
        filtered_viz = draw_detections(frame_bgr, filtered, with_labels=True)
        filtered_cropped = crop_to_roi(filtered_viz, geometry)
        comparison = create_side_by_side(filtered_cropped, original_cropped,
                                        f"Filtered ({len(filtered)})", "Original")
        cv2.imwrite(str(stage_dirs[5] / f"frame_{frame_idx:04d}.png"), comparison)
        
        # Stage 6: Classification
        print("  Stage 6: Classification...")
        balls = classifier.classify(filtered, geometry.px_per_mm)
        
        class_counts = {}
        for ball in balls:
            cls = ball.cls
            class_counts[cls] = class_counts.get(cls, 0) + 1
        frame_stats["class_counts"] = class_counts
        print(f"    Classes: {class_counts}")
        
        classified_viz = draw_detections(frame_bgr, balls, with_labels=True)
        classified_cropped = crop_to_roi(classified_viz, geometry)
        comparison = create_side_by_side(classified_cropped, original_cropped,
                                        f"Classified {class_counts}", "Original")
        cv2.imwrite(str(stage_dirs[6] / f"frame_{frame_idx:04d}.png"), comparison)
        
        summary["frames_processed"].append(frame_stats)
        print(f"  Frame {frame_idx} complete!")
    
    loader.close()
    
    # Save summary JSON
    import json
    with open(base_path / "validation_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n=== Validation Complete ===")
    print(f"Output saved to: {base_path}")
    print(f"  01_drum_geometry/  - Drum detection and calibration")
    print(f"  02_preprocessing/  - 6-stage preprocessing output")
    print(f"  03_detection/      - Raw circle candidates")
    print(f"  04_scoring/        - Confidence scoring")
    print(f"  05_filtering/      - 4-stage filtering")
    print(f"  06_classification/ - Size class assignment")


def main():
    parser = argparse.ArgumentParser(description="Validate MillPresenter pipeline")
    parser.add_argument("--video", "-v", required=True, help="Path to input video")
    parser.add_argument("--output", "-o", default="validation_output", help="Output directory")
    parser.add_argument("--frames", "-f", type=int, nargs="+", default=[0, 50, 100],
                       help="Frame indices to process")
    parser.add_argument("--drum-diameter", "-d", type=float, default=200.0,
                       help="Drum diameter in mm")
    
    args = parser.parse_args()
    
    validate_pipeline(
        video_path=args.video,
        output_dir=args.output,
        frame_indices=args.frames,
        drum_diameter_mm=args.drum_diameter
    )


if __name__ == "__main__":
    main()
