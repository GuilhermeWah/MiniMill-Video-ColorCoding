"""
STEP_06 Test Script: Filtering and Cleanup

This script:
1. Loads scored detections from STEP_05
2. Applies 3-stage filtering (rim, confidence, NMS)
3. Generates before/after comparison overlays
4. Produces statistics on filter effectiveness
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

from config import FILTER_CONFIG
from filter import (
    apply_filters,
    create_filter_overlay,
    imread_unicode,
    imwrite_unicode,
    FilteredDetection,
    FilterStats
)


def load_geometry_for_video(video_name: str, project_root: Path) -> dict:
    """Load cached geometry for a video."""
    import hashlib
    
    # Generate hash from video filename
    video_filename = f"{video_name}.MOV"
    hash_part = hashlib.md5(video_filename.encode()).hexdigest()[:8]
    cache_name = f"{video_name}_{hash_part}.json"
    
    # Try cache directory first
    cache_path = project_root / "cache" / "geometry" / cache_name
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)
    
    # Try config directory
    config_path = project_root / "config" / cache_name
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    
    raise FileNotFoundError(f"No geometry found for {video_name}")


def main():
    """Run filtering on all golden frames."""
    
    project_root = Path(__file__).parent.parent
    golden_dir = project_root / "data" / "golden_frames"
    confidence_dir = project_root / "output" / "confidence_test"
    output_dir = project_root / "output" / "filter_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load golden manifest
    manifest_path = golden_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: Golden manifest not found: {manifest_path}")
        return
    
    with open(manifest_path) as f:
        golden_manifest = json.load(f)
    
    print("=" * 60)
    print("STEP_06: Filtering and Cleanup Test")
    print("=" * 60)
    print(f"\nUsing FILTER_CONFIG:")
    for k, v in FILTER_CONFIG.items():
        print(f"  {k}: {v}")
    print()
    
    results = []
    all_stats = {
        "input_total": 0,
        "after_rim_total": 0,
        "after_conf_total": 0,
        "after_nms_total": 0,
    }
    
    # Cache geometry per video
    geometry_cache = {}
    
    for entry in golden_manifest["frames"]:
        video_full = entry["video"]
        video_name = Path(video_full).stem  # Remove .MOV
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
        
        # Load scored detections from STEP_05
        scored_json_path = confidence_dir / f"{video_name}_frame_{frame_idx}_scored.json"
        if not scored_json_path.exists():
            print(f"  SKIP: Scored detections not found: {scored_json_path.name}")
            continue
        
        with open(scored_json_path) as f:
            scored_data = json.load(f)
        
        detections = scored_data["detections"]
        print(f"  Input: {len(detections)} candidates")
        
        # Apply filters
        filtered, stats = apply_filters(
            detections, drum_center, drum_radius, FILTER_CONFIG
        )
        
        print(f"  After rim filter: {stats.after_rim} ({stats.rim_rejected} rejected)")
        print(f"  After confidence: {stats.after_confidence} ({stats.confidence_rejected} rejected)")
        print(f"  After NMS: {stats.after_nms} ({stats.nms_suppressed} suppressed)")
        print(f"  Retention rate: {stats.to_dict()['retention_rate'] * 100:.1f}%")
        
        # Accumulate totals
        all_stats["input_total"] += stats.input_count
        all_stats["after_rim_total"] += stats.after_rim
        all_stats["after_conf_total"] += stats.after_confidence
        all_stats["after_nms_total"] += stats.after_nms
        
        # Load frame for overlay
        frame = imread_unicode(raw_path)
        if frame is None:
            print(f"  ERROR: Could not load frame: {raw_path}")
            continue
        
        # Create overlay
        overlay = create_filter_overlay(
            frame, detections, filtered,
            drum_center, drum_radius,
            FILTER_CONFIG.get("rim_margin_ratio", 0.12)
        )
        
        # Save overlay
        overlay_path = output_dir / f"{video_name}_frame_{frame_idx}_filtered.png"
        imwrite_unicode(overlay_path, overlay)
        print(f"  Saved: {overlay_path.name}")
        
        # Save filtered detections JSON
        filter_data = {
            "video": video_name,
            "frame_idx": frame_idx,
            "config_used": FILTER_CONFIG,
            "geometry": {
                "center": drum_center,
                "radius": drum_radius
            },
            "stats": stats.to_dict(),
            "detections": [d.to_dict() for d in filtered]
        }
        
        json_path = output_dir / f"{video_name}_frame_{frame_idx}_filtered.json"
        with open(json_path, 'w') as f:
            json.dump(filter_data, f, indent=2)
        
        results.append({
            "video": video_name,
            "frame_idx": frame_idx,
            "input": stats.input_count,
            "after_rim": stats.after_rim,
            "after_conf": stats.after_confidence,
            "after_nms": stats.after_nms,
            "retention_rate": stats.to_dict()["retention_rate"],
            "overlay_path": str(overlay_path.relative_to(project_root)),
            "json_path": str(json_path.relative_to(project_root))
        })
    
    # Overall summary
    print("\n" + "=" * 60)
    print("OVERALL SUMMARY")
    print("=" * 60)
    
    total_input = all_stats["input_total"]
    total_output = all_stats["after_nms_total"]
    
    print(f"\nTotal input detections: {total_input}")
    print(f"After rim filter: {all_stats['after_rim_total']} ({100*(1-all_stats['after_rim_total']/total_input):.1f}% rejected)")
    print(f"After confidence: {all_stats['after_conf_total']} ({100*(1-all_stats['after_conf_total']/all_stats['after_rim_total']):.1f}% rejected)")
    print(f"After NMS: {all_stats['after_nms_total']} ({100*(1-all_stats['after_nms_total']/all_stats['after_conf_total']):.1f}% suppressed)")
    print(f"\nFinal output: {total_output} detections")
    print(f"Overall reduction: {100*(1-total_output/total_input):.1f}%")
    print(f"Retention rate: {100*total_output/total_input:.1f}%")
    
    # Per-video summary
    print("\nPer-video summary:")
    videos = set(r["video"] for r in results)
    for video in sorted(videos):
        video_results = [r for r in results if r["video"] == video]
        total_in = sum(r["input"] for r in video_results)
        total_out = sum(r["after_nms"] for r in video_results)
        retention = total_out / total_in if total_in > 0 else 0
        print(f"  {video}:")
        print(f"    Input: {total_in} → Output: {total_out} ({retention*100:.1f}% retained)")
    
    # Save manifest
    manifest = {
        "step": "STEP_06",
        "description": "Filtering and cleanup results",
        "timestamp": datetime.now().isoformat(),
        "config": FILTER_CONFIG,
        "global_stats": {
            "input_total": total_input,
            "after_rim": all_stats["after_rim_total"],
            "after_confidence": all_stats["after_conf_total"],
            "after_nms": all_stats["after_nms_total"],
            "overall_reduction": round(1 - total_output/total_input, 4) if total_input > 0 else 0,
            "retention_rate": round(total_output/total_input, 4) if total_input > 0 else 0
        },
        "frames": results
    }
    
    manifest_path = output_dir / "filter_manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved: {manifest_path}")
    
    print("\n" + "=" * 60)
    print("STEP_06 Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
