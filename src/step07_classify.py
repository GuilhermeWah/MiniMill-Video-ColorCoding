"""
STEP_07 Test Script: Size Classification

This script:
1. Loads filtered detections from STEP_06
2. Calculates px_per_mm from drum geometry
3. Classifies each detection into size bins (4mm, 6mm, 8mm, 10mm)
4. Generates color-coded overlays by size class
5. Produces distribution statistics
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

import cv2
import numpy as np

from config import SIZE_CONFIG, FILTER_CONFIG
from classify import (
    classify_detections,
    calculate_px_per_mm,
    get_class_color,
    ClassifiedDetection,
    ClassificationStats
)


def imread_unicode(path):
    """Read image with Unicode path support."""
    path_str = str(path)
    try:
        with open(path_str, 'rb') as f:
            data = np.frombuffer(f.read(), dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"  Error reading image: {e}")
        return None


def imwrite_unicode(path, img):
    """Write image with Unicode path support."""
    path_str = str(path)
    try:
        ext = Path(path_str).suffix.lower()
        success, encoded = cv2.imencode(ext, img)
        if success:
            with open(path_str, 'wb') as f:
                f.write(encoded.tobytes())
            return True
    except Exception as e:
        print(f"  Error writing image: {e}")
    return False


def load_geometry_for_video(video_name: str, project_root: Path) -> dict:
    """Load cached geometry for a video."""
    import hashlib
    
    video_filename = f"{video_name}.MOV"
    hash_part = hashlib.md5(video_filename.encode()).hexdigest()[:8]
    cache_name = f"{video_name}_{hash_part}.json"
    
    cache_path = project_root / "cache" / "geometry" / cache_name
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)
    
    config_path = project_root / "config" / cache_name
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    
    raise FileNotFoundError(f"No geometry found for {video_name}")


def create_classification_overlay(
    frame: np.ndarray,
    classified_detections: list,
    drum_center: tuple,
    drum_radius: int,
    size_config: dict
) -> np.ndarray:
    """
    Create overlay with color-coded size classes.
    
    Args:
        frame: Original BGR frame
        classified_detections: List of ClassifiedDetection objects
        drum_center: (cx, cy) drum center
        drum_radius: Drum radius in pixels
        size_config: Configuration with class_colors
        
    Returns:
        Overlay image
    """
    # Create a copy for drawing (will be blended)
    overlay = frame.copy()
    
    # Draw drum ROI circle
    cv2.circle(overlay, drum_center, drum_radius, (100, 100, 100), 2)
    
    # Get color scheme
    class_colors = size_config.get("class_colors", {
        "4mm": (0, 0, 255),
        "6mm": (0, 255, 0),
        "8mm": (255, 0, 0),
        "10mm": (0, 255, 255),
        "unknown": (128, 128, 128)
    })
    
    show_label = size_config.get("show_size_label", False)
    font_scale = size_config.get("label_font_scale", 0.5)
    circle_thickness = size_config.get("circle_thickness", 2)
    center_dot_radius = size_config.get("center_dot_radius", 2)
    use_aa = size_config.get("use_antialiasing", True)
    line_type = cv2.LINE_AA if use_aa else cv2.LINE_8
    
    # Draw each detection on overlay
    for det in classified_detections:
        color = class_colors.get(det.cls, (128, 128, 128))
        center = (det.x, det.y)
        radius = int(det.r_px)
        
        # Draw circle outline with anti-aliasing
        cv2.circle(overlay, center, radius, color, circle_thickness, line_type)
        cv2.circle(overlay, center, center_dot_radius, color, -1, line_type)
        
        # Draw label
        if show_label:
            label = det.cls
            label_pos = (det.x + radius + 3, det.y - 3)
            cv2.putText(overlay, label, label_pos, cv2.FONT_HERSHEY_SIMPLEX,
                       font_scale, color, 1, cv2.LINE_AA)
    
    # Apply opacity blending
    opacity = size_config.get("overlay_opacity", 0.7)
    result = cv2.addWeighted(overlay, opacity, frame, 1 - opacity, 0)
    
    return result


def create_legend(size_config: dict, stats: ClassificationStats) -> np.ndarray:
    """Create a legend image showing class colors and counts."""
    legend_height = 150
    legend_width = 200
    legend = np.zeros((legend_height, legend_width, 3), dtype=np.uint8)
    legend[:] = (40, 40, 40)  # Dark gray background
    
    class_colors = size_config.get("class_colors", {})
    classes = ["4mm", "6mm", "8mm", "10mm", "unknown"]
    counts = {
        "4mm": stats.count_4mm,
        "6mm": stats.count_6mm,
        "8mm": stats.count_8mm,
        "10mm": stats.count_10mm,
        "unknown": stats.count_unknown
    }
    
    y = 25
    for cls in classes:
        color = class_colors.get(cls, (128, 128, 128))
        count = counts[cls]
        
        # Color swatch
        cv2.rectangle(legend, (10, y-12), (30, y+2), color, -1)
        
        # Label with count
        text = f"{cls}: {count}"
        cv2.putText(legend, text, (40, y), cv2.FONT_HERSHEY_SIMPLEX,
                   0.5, (255, 255, 255), 1, cv2.LINE_AA)
        y += 25
    
    return legend


def main():
    """Run classification on all golden frames."""
    
    project_root = Path(__file__).parent.parent
    golden_dir = project_root / "data" / "golden_frames"
    filter_dir = project_root / "output" / "filter_test"
    output_dir = project_root / "output" / "classify_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load golden manifest
    manifest_path = golden_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: Golden manifest not found: {manifest_path}")
        return
    
    with open(manifest_path) as f:
        golden_manifest = json.load(f)
    
    print("=" * 60)
    print("STEP_07: Size Classification Test")
    print("=" * 60)
    print(f"\nUsing SIZE_CONFIG:")
    print(f"  drum_diameter_mm: {SIZE_CONFIG['drum_diameter_mm']}")
    print(f"  size_bins:")
    for cls, (min_mm, max_mm) in SIZE_CONFIG['size_bins'].items():
        print(f"    {cls}: {min_mm:.1f} - {max_mm:.1f} mm")
    print()
    
    results = []
    total_by_class = {"4mm": 0, "6mm": 0, "8mm": 0, "10mm": 0, "unknown": 0}
    total_count = 0
    
    geometry_cache = {}
    px_per_mm_cache = {}
    
    for entry in golden_manifest["frames"]:
        video_full = entry["video"]
        video_name = Path(video_full).stem
        frame_idx = entry["frame_idx"]
        raw_path = golden_dir / entry["files"]["raw"]
        
        print(f"\nProcessing: {video_name} frame {frame_idx}")
        
        # Load geometry (cached per video)
        if video_name not in geometry_cache:
            try:
                geometry_cache[video_name] = load_geometry_for_video(video_name, project_root)
            except FileNotFoundError as e:
                print(f"  ERROR: {e}")
                continue
        
        geom = geometry_cache[video_name]
        drum_center = (geom["drum_center_x_px"], geom["drum_center_y_px"])
        drum_radius = geom["drum_radius_px"]
        
        # Calculate px_per_mm (cached per video)
        if video_name not in px_per_mm_cache:
            px_per_mm = calculate_px_per_mm(
                drum_radius,
                SIZE_CONFIG["drum_diameter_mm"]
            )
            px_per_mm_cache[video_name] = px_per_mm
            print(f"  Calibration: drum_radius={drum_radius}px, px_per_mm={px_per_mm:.3f}")
        else:
            px_per_mm = px_per_mm_cache[video_name]
        
        # Load filtered detections from STEP_06
        filtered_json_path = filter_dir / f"{video_name}_frame_{frame_idx}_filtered.json"
        if not filtered_json_path.exists():
            print(f"  SKIP: Filtered detections not found: {filtered_json_path.name}")
            continue
        
        with open(filtered_json_path) as f:
            filtered_data = json.load(f)
        
        detections = filtered_data["detections"]
        print(f"  Input: {len(detections)} filtered detections")
        
        # Classify detections
        classified, stats = classify_detections(detections, px_per_mm, SIZE_CONFIG)
        
        print(f"  Classification results:")
        print(f"    4mm:  {stats.count_4mm:3d} ({stats.to_dict()['percentages']['4mm']:5.1f}%)")
        print(f"    6mm:  {stats.count_6mm:3d} ({stats.to_dict()['percentages']['6mm']:5.1f}%)")
        print(f"    8mm:  {stats.count_8mm:3d} ({stats.to_dict()['percentages']['8mm']:5.1f}%)")
        print(f"    10mm: {stats.count_10mm:3d} ({stats.to_dict()['percentages']['10mm']:5.1f}%)")
        if stats.count_unknown > 0:
            print(f"    unknown: {stats.count_unknown:3d}")
        
        # Accumulate totals
        total_count += stats.total_count
        total_by_class["4mm"] += stats.count_4mm
        total_by_class["6mm"] += stats.count_6mm
        total_by_class["8mm"] += stats.count_8mm
        total_by_class["10mm"] += stats.count_10mm
        total_by_class["unknown"] += stats.count_unknown
        
        # Load frame for overlay
        frame = imread_unicode(raw_path)
        if frame is None:
            print(f"  ERROR: Could not load frame: {raw_path}")
            continue
        
        # Create overlay
        overlay = create_classification_overlay(
            frame, classified, drum_center, drum_radius, SIZE_CONFIG
        )
        
        # Create and embed legend
        legend = create_legend(SIZE_CONFIG, stats)
        h, w = legend.shape[:2]
        overlay[10:10+h, 10:10+w] = legend
        
        # Save outputs
        overlay_path = output_dir / f"{video_name}_frame_{frame_idx}_classified.png"
        imwrite_unicode(overlay_path, overlay)
        
        # Save JSON with classifications
        json_path = output_dir / f"{video_name}_frame_{frame_idx}_classified.json"
        output_data = {
            "video": video_name,
            "frame_idx": frame_idx,
            "px_per_mm": round(px_per_mm, 3),
            "drum_radius_px": drum_radius,
            "classification_stats": stats.to_dict(),
            "detections": [d.to_dict() for d in classified]
        }
        with open(json_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        results.append({
            "video": video_name,
            "frame_idx": frame_idx,
            "px_per_mm": round(px_per_mm, 3),
            "stats": stats.to_dict()
        })
        
        print(f"  Saved: {overlay_path.name}")
    
    # Summary
    print("\n" + "=" * 60)
    print("CLASSIFICATION SUMMARY")
    print("=" * 60)
    
    print(f"\nTotal detections classified: {total_count}")
    print(f"\nDistribution across all frames:")
    for cls in ["4mm", "6mm", "8mm", "10mm", "unknown"]:
        count = total_by_class[cls]
        pct = 100 * count / total_count if total_count > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {cls:8s}: {count:4d} ({pct:5.1f}%) {bar}")
    
    print(f"\nCalibration values used:")
    for video_name, px_per_mm in px_per_mm_cache.items():
        geom = geometry_cache[video_name]
        print(f"  {video_name}: drum_r={geom['drum_radius_px']}px, px_per_mm={px_per_mm:.3f}")
    
    # Save summary JSON
    summary_path = output_dir / "classification_summary.json"
    summary = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "drum_diameter_mm": SIZE_CONFIG["drum_diameter_mm"],
            "size_bins": SIZE_CONFIG["size_bins"]
        },
        "calibrations": {k: round(v, 3) for k, v in px_per_mm_cache.items()},
        "total_count": total_count,
        "total_by_class": total_by_class,
        "percentages": {
            cls: round(100 * count / total_count, 1) if total_count > 0 else 0
            for cls, count in total_by_class.items()
        },
        "per_frame_results": results
    }
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nSummary saved: {summary_path}")
    print(f"Overlays saved to: {output_dir}")


if __name__ == "__main__":
    main()
