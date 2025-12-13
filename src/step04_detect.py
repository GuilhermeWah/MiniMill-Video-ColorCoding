"""
STEP_04: Candidate Generation - Test Script

This script runs circle detection on all golden frames and generates:
- Detection overlay images
- Raw candidate JSON files
- Detection manifest with statistics
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
SRC_DIR = Path(__file__).parent
BASE_DIR = SRC_DIR.parent
sys.path.insert(0, str(SRC_DIR))

import cv2
import numpy as np
from detect import (
    detect_candidates,
    create_detection_overlay,
    imread_unicode,
    imwrite_unicode
)
from preprocess import preprocess_frame
from config import DETECTION_BEAD_CONFIG, PREPROCESS_CONFIG, DrumGeometry


def generate_roi_mask(width: int, height: int, geometry: DrumGeometry) -> np.ndarray:
    """Generate binary ROI mask from drum geometry (full radius)."""
    mask = np.zeros((height, width), dtype=np.uint8)
    center = (geometry.drum_center_x_px, geometry.drum_center_y_px)
    radius = geometry.drum_radius_px
    cv2.circle(mask, center, radius, 255, -1)
    return mask


def main():
    """Run detection on all golden frames."""
    
    # Paths
    GOLDEN_DIR = BASE_DIR / "data" / "golden_frames"
    OUTPUT_DIR = BASE_DIR / "output" / "detection_test"
    CACHE_DIR = BASE_DIR / "cache" / "geometry"
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("STEP_04: Candidate Generation (Circle Detection)")
    print("=" * 60)
    print()
    
    # Load golden frames manifest
    manifest_path = GOLDEN_DIR / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: Golden frames manifest not found: {manifest_path}")
        return
    
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    print(f"Loaded {len(manifest['frames'])} golden frames from manifest")
    print(f"Detection config: {DETECTION_BEAD_CONFIG}")
    print()
    
    # Geometry cache files
    cache_files = {
        'IMG_6535': CACHE_DIR / 'IMG_6535_8d05444a.json',
        'IMG_1276': CACHE_DIR / 'IMG_1276_2e8f9de2.json',
        'DSC_3310': CACHE_DIR / 'DSC_3310_abb19bc1.json',
    }
    
    # Load geometries
    geometry_cache = {}
    for video_name, cache_file in cache_files.items():
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                data = json.load(f)
            geometry_cache[video_name] = DrumGeometry.from_dict(data)
            print(f"Loaded geometry: {video_name} (r={data['drum_radius_px']}px)")
    
    print()
    
    # Track results
    results = []
    all_counts = []
    
    for frame_info in manifest['frames']:
        frame_id = frame_info['id']
        video_name = frame_info['video'].split('.')[0]
        
        print(f"Processing: {frame_id}")
        
        # Load raw frame
        frame_path = GOLDEN_DIR / f"{frame_id}.png"
        if not frame_path.exists():
            print(f"  WARNING: Frame not found: {frame_path}")
            continue
        
        frame = imread_unicode(frame_path)
        if frame is None:
            print(f"  WARNING: Failed to load: {frame_path}")
            continue
        
        h, w = frame.shape[:2]
        
        # Get geometry
        geometry = geometry_cache.get(video_name)
        if geometry is None:
            print(f"  WARNING: No geometry for {video_name}")
            continue
        
        # Generate ROI mask
        roi_mask = generate_roi_mask(w, h, geometry)
        
        # Preprocess frame
        preprocess_result = preprocess_frame(frame, roi_mask, PREPROCESS_CONFIG)
        preprocessed = preprocess_result.preprocessed
        
        # Run detection
        detection_result = detect_candidates(
            preprocessed,
            geometry.drum_radius_px,
            DETECTION_BEAD_CONFIG
        )
        
        count = len(detection_result.candidates)
        all_counts.append(count)
        
        # Print stats
        params = detection_result.params_used
        print(f"  Resolution: {w}x{h}")
        print(f"  Radius range: {params['minRadius']}-{params['maxRadius']}px")
        print(f"  Candidates detected: {count}")
        
        # Create overlay on original color frame
        overlay = create_detection_overlay(frame, detection_result)
        
        # Save outputs
        overlay_path = OUTPUT_DIR / f"{frame_id}_candidates.png"
        imwrite_unicode(overlay_path, overlay)
        
        json_path = OUTPUT_DIR / f"{frame_id}_candidates.json"
        with open(json_path, 'w') as f:
            json.dump(detection_result.to_dict(), f, indent=2)
        
        print(f"  Saved: {overlay_path.name}, {json_path.name}")
        print()
        
        # Track result
        results.append({
            'frame_id': frame_id,
            'video': frame_info['video'],
            'resolution': f"{w}x{h}",
            'candidate_count': count,
            'params': params,
            'outputs': {
                'overlay': str(overlay_path.relative_to(BASE_DIR)),
                'json': str(json_path.relative_to(BASE_DIR)),
            }
        })
    
    # Compute stats
    if all_counts:
        stats = {
            'total_candidates': sum(all_counts),
            'avg_per_frame': sum(all_counts) / len(all_counts),
            'min_per_frame': min(all_counts),
            'max_per_frame': max(all_counts),
        }
    else:
        stats = {}
    
    # Save manifest
    run_manifest = {
        'step': 'STEP_04',
        'title': 'Candidate Generation (Circle Detection)',
        'timestamp': datetime.now().isoformat(),
        'config': DETECTION_BEAD_CONFIG,
        'frames_processed': len(results),
        'statistics': stats,
        'results': results,
    }
    
    manifest_out = OUTPUT_DIR / "detection_manifest.json"
    with open(manifest_out, 'w') as f:
        json.dump(run_manifest, f, indent=2)
    print(f"Manifest saved: {manifest_out}")
    
    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Frames processed: {len(results)}")
    if stats:
        print(f"Total candidates: {stats['total_candidates']}")
        print(f"Avg per frame: {stats['avg_per_frame']:.1f}")
        print(f"Range: {stats['min_per_frame']} - {stats['max_per_frame']}")
    print()
    print(f"Outputs saved to: {OUTPUT_DIR}")
    print("Done!")


if __name__ == "__main__":
    main()
