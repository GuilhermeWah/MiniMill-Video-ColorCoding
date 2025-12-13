"""
STEP_01 Main Script

Implements `Drum Geometry & ROI Stabilization`.

REFACTOR (2025-12-12, PM Approved):
- Auto-detects drum geometry using HoughCircles
- Caches geometry per video in cache/geometry/
- Resolution-agnostic (works with 4K, 1080p, any resolution)

Directory Structure:
- config/                     Production configs (version-controlled)
  - geometry_overrides.json   Manual overrides
- cache/geometry/             Auto-generated cache (gitignored)
  - {video}_{hash}.json       Per-video cached geometry
- output/debug/               Debug outputs (gitignored)
  - roi_mask.png
  - geometry_overlay.png
"""

import argparse
import cv2
import json
import os
import sys
from datetime import datetime

# Local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import (
    load_geometry_for_video, save_geometry, get_geometry_cache_path,
    DETECTION_CONFIG, CONFIG_DIR, CACHE_DIR, GEOMETRY_CACHE_DIR, DEBUG_DIR
)
from src.drum import generate_roi_mask, create_geometry_overlay, validate_geometry, imwrite_unicode

def main():
    parser = argparse.ArgumentParser(
        description="STEP_01: Drum Geometry & ROI Stabilization with Auto-Detection"
    )
    parser.add_argument("--video", required=True, help="Path to input video")
    parser.add_argument("--frames", default="0,100", help="Comma-sep frame indices")
    parser.add_argument("--output-dir", default=None, help="Debug output directory")
    parser.add_argument("--force-detect", action="store_true", 
                        help="Force re-detection even if cached geometry exists")
    args = parser.parse_args()
    
    start_time = datetime.now()
    
    # Paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    video_path = args.video if os.path.isabs(args.video) else os.path.join(project_root, args.video)
    video_name = os.path.splitext(os.path.basename(video_path))[0]  # e.g., "IMG_1276"
    
    # Use new directory structure with video-specific debug subdirectory
    config_dir = os.path.join(project_root, CONFIG_DIR)
    cache_dir = os.path.join(project_root, GEOMETRY_CACHE_DIR)
    base_debug_dir = args.output_dir if args.output_dir else os.path.join(project_root, DEBUG_DIR)
    debug_dir = os.path.join(base_debug_dir, video_name)  # Per-video subdirectory
    
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(debug_dir, exist_ok=True)

    # 1. Load Video & Frames
    if not os.path.exists(video_path):
        print(f"Error: Video not found at {video_path}")
        sys.exit(1)
        
    cap = cv2.VideoCapture(video_path)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_indices = [int(x) for x in args.frames.split(",")]
    loaded_frames = {}
    
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            loaded_frames[idx] = frame
        else:
            print(f"Warning: Could not read frame {idx}")
            
    cap.release()
    
    if not loaded_frames:
        print("Error: No frames loaded.")
        sys.exit(1)
        
    reference_frame = next(iter(loaded_frames.values()))
    frame_shape = reference_frame.shape
    
    print(f"Video: {os.path.basename(video_path)}")
    print(f"Resolution: {frame_width}x{frame_height}")
    
    # 2. Load or Auto-Detect Geometry (per-video)
    geometry, status_msg = load_geometry_for_video(
        video_path=video_path,
        frame=reference_frame,
        config_dir=config_dir,
        cache_dir=cache_dir,
        force_detect=args.force_detect
    )
    print(f"Geometry: {status_msg}")
    print(f"  Source: {geometry.source}")
    print(f"  Center: ({geometry.drum_center_x_px}, {geometry.drum_center_y_px})")
    print(f"  Radius: {geometry.drum_radius_px}px (effective: {geometry.effective_radius_px}px)")
    
    # Get the per-video cache path
    geometry_cache_path = get_geometry_cache_path(video_path, cache_dir)
    
    # Validate
    if not validate_geometry(geometry, frame_shape):
        print("Warning: Geometry parameters appear invalid for this frame size.")
        
    # 3. Generate Debug Artifacts
    
    # ROI Mask (Binary)
    roi_mask = generate_roi_mask(geometry, frame_shape)
    roi_mask_path = os.path.join(debug_dir, "roi_mask.png")
    imwrite_unicode(roi_mask_path, roi_mask)
    
    # Geometry Overlay (Debug)
    # Generate for ALL requested test frames
    overlay_paths = []
    
    # Primary overlay (required artifact name)
    primary_overlay_path = os.path.join(debug_dir, "geometry_overlay.png")
    imwrite_unicode(primary_overlay_path, create_geometry_overlay(reference_frame, geometry))
    
    for idx, frame in loaded_frames.items():
        fname = f"geometry_overlay_frame_{idx}.png"
        fpath = os.path.join(debug_dir, fname)
        imwrite_unicode(fpath, create_geometry_overlay(frame, geometry))
        overlay_paths.append(fname)

    # 4. Geometry already cached by load_geometry_for_video if auto-detected
    # Save again to ensure it's up to date
    save_geometry(geometry, geometry_cache_path)
    
    # 5. Manifest (in debug dir)
    end_time = datetime.now()
    manifest = {
        "step_id": "STEP_01",
        "timestamp": end_time.isoformat(),
        "duration_sec": (end_time - start_time).total_seconds(),
        "input": {
            "video": video_path,
            "video_resolution": f"{frame_width}x{frame_height}",
            "frames": frame_indices
        },
        "detection_config": DETECTION_CONFIG,
        "geometry": geometry.to_dict(),
        "paths": {
            "config_dir": config_dir,
            "cache_dir": cache_dir,
            "debug_dir": debug_dir
        },
        "artifacts": {
            "geometry_cache": geometry_cache_path,
            "roi_mask": roi_mask_path,
            "overlay_primary": primary_overlay_path,
            "overlays_all": overlay_paths
        }
    }
    
    manifest_path = os.path.join(debug_dir, "run_manifest.json")
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\nArtifacts:")
    print(f"  Cache: {geometry_cache_path}")
    print(f"  Debug: {debug_dir}/")
    print("STEP_01 Complete.")

if __name__ == "__main__":
    main()
