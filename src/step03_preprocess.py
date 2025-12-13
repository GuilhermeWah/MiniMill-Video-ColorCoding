"""
STEP_03: Preprocessing Baseline Stabilization - Test Script

This script runs the preprocessing pipeline on all golden frames and generates:
- Before/after comparison images
- Stage-by-stage visualization
- Quality metrics JSON
- Comparison grid of all frames
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path for imports
SRC_DIR = Path(__file__).parent
BASE_DIR = SRC_DIR.parent
sys.path.insert(0, str(SRC_DIR))

import cv2
import numpy as np
from preprocess import (
    preprocess_frame,
    create_stages_visualization,
    create_before_after_comparison,
    imread_unicode,
    imwrite_unicode
)
from config import PREPROCESS_CONFIG, DrumGeometry


def generate_roi_mask(width: int, height: int, geometry: DrumGeometry) -> np.ndarray:
    """Generate binary ROI mask from drum geometry.
    
    NOTE: For preprocessing, we use the FULL drum radius (not effective_radius)
    to avoid cutting off beads near the edge. The rim margin is applied later
    during detection filtering, not during preprocessing.
    """
    mask = np.zeros((height, width), dtype=np.uint8)
    center = (geometry.drum_center_x_px, geometry.drum_center_y_px)
    # Use full radius for preprocessing (not effective_radius which subtracts margin)
    radius = geometry.drum_radius_px
    cv2.circle(mask, center, radius, 255, -1)
    return mask


def main():
    """Run preprocessing on all golden frames."""
    
    # Paths
    GOLDEN_DIR = BASE_DIR / "data" / "golden_frames"
    OUTPUT_DIR = BASE_DIR / "output" / "preprocess_test"
    DATA_DIR = BASE_DIR / "data"
    CACHE_DIR = BASE_DIR / "cache" / "geometry"
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("STEP_03: Preprocessing Baseline Stabilization")
    print("=" * 60)
    print()
    
    # Load golden frames manifest
    manifest_path = GOLDEN_DIR / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: Golden frames manifest not found: {manifest_path}")
        print("Run STEP_02 first to generate golden frames.")
        return
    
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    print(f"Loaded {len(manifest['frames'])} golden frames from manifest")
    print(f"Config: {PREPROCESS_CONFIG}")
    print()
    
    # Video name to geometry - load from cache files directly
    geometry_cache = {}
    cache_files = {
        'IMG_6535': CACHE_DIR / 'IMG_6535_8d05444a.json',
        'IMG_1276': CACHE_DIR / 'IMG_1276_2e8f9de2.json',
        'DSC_3310': CACHE_DIR / 'DSC_3310_abb19bc1.json',
    }
    
    # Track results
    results = []
    all_metrics = []
    comparison_images = []
    
    for frame_info in manifest['frames']:
        frame_id = frame_info['id']
        video_name = frame_info['video'].split('.')[0]  # Remove extension
        
        print(f"Processing: {frame_id}")
        
        # Load frame (use raw, not masked - we'll apply mask in preprocessing)
        frame_path = GOLDEN_DIR / f"{frame_id}.png"
        if not frame_path.exists():
            print(f"  WARNING: Frame not found: {frame_path}")
            continue
        
        frame = imread_unicode(frame_path)
        if frame is None:
            print(f"  WARNING: Failed to load: {frame_path}")
            continue
        
        h, w = frame.shape[:2]
        
        # Load geometry from cache
        if video_name not in geometry_cache:
            cache_file = cache_files.get(video_name)
            if cache_file and cache_file.exists():
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                geometry = DrumGeometry.from_dict(data)
                geometry_cache[video_name] = geometry
                print(f"  Geometry: Loaded from {cache_file.name}")
            else:
                print(f"  WARNING: Cache not found: {cache_file}")
                geometry_cache[video_name] = None
        
        geometry = geometry_cache.get(video_name)
        
        # Generate ROI mask
        if geometry:
            roi_mask = generate_roi_mask(w, h, geometry)
        else:
            roi_mask = None
            print(f"  WARNING: No geometry for {video_name}, skipping ROI mask")
        
        # Run preprocessing
        result = preprocess_frame(frame, roi_mask, PREPROCESS_CONFIG)
        
        # Save outputs
        # 1. Original (reference)
        original_path = OUTPUT_DIR / f"{frame_id}_original.png"
        imwrite_unicode(original_path, result.original)
        
        # 2. Preprocessed
        preprocessed_path = OUTPUT_DIR / f"{frame_id}_preprocessed.png"
        imwrite_unicode(preprocessed_path, result.preprocessed)
        
        # 3. Stages visualization
        stages_viz = create_stages_visualization(result.stages)
        stages_path = OUTPUT_DIR / f"{frame_id}_stages.png"
        imwrite_unicode(stages_path, stages_viz)
        
        # 4. Before/after comparison
        comparison = create_before_after_comparison(
            result.original, 
            result.preprocessed,
            result.metrics,
            title=frame_id
        )
        comparison_path = OUTPUT_DIR / f"{frame_id}_comparison.png"
        imwrite_unicode(comparison_path, comparison)
        
        # Track for grid
        comparison_images.append((frame_id, comparison))
        
        # Print metrics
        m = result.metrics
        print(f"  Resolution: {w}x{h}")
        print(f"  Edge clarity: {m['edge_clarity']:.0f}")
        print(f"  Contrast: {m['contrast_before']:.1f} -> {m['contrast_after']:.1f}")
        print(f"  Glare: {m['glare_pct_before']:.2f}% -> {m['glare_pct_after']:.2f}%")
        print(f"  Histogram: {m['histogram_min']} - {m['histogram_max']} (spread: {m['histogram_spread']})")
        print()
        
        # Store result
        results.append({
            'frame_id': frame_id,
            'video': frame_info['video'],
            'resolution': f"{w}x{h}",
            'metrics': m,
            'outputs': {
                'original': str(original_path.relative_to(BASE_DIR)),
                'preprocessed': str(preprocessed_path.relative_to(BASE_DIR)),
                'stages': str(stages_path.relative_to(BASE_DIR)),
                'comparison': str(comparison_path.relative_to(BASE_DIR)),
            }
        })
        all_metrics.append(m)
    
    # Create comparison grid (all frames)
    print("Creating comparison grid...")
    grid = create_comparison_grid(comparison_images, max_cols=3)
    grid_path = OUTPUT_DIR / "comparison_grid.png"
    imwrite_unicode(grid_path, grid)
    print(f"  Saved: {grid_path}")
    
    # Compute aggregate metrics
    if all_metrics:
        avg_metrics = {
            'edge_clarity_avg': np.mean([m['edge_clarity'] for m in all_metrics]),
            'contrast_improvement_avg': np.mean([
                m['contrast_after'] - m['contrast_before'] for m in all_metrics
            ]),
            'glare_reduction_avg': np.mean([
                m['glare_pct_before'] - m['glare_pct_after'] for m in all_metrics
            ]),
        }
    else:
        avg_metrics = {}
    
    # Save manifest
    run_manifest = {
        'step': 'STEP_03',
        'title': 'Preprocessing Baseline Stabilization',
        'timestamp': datetime.now().isoformat(),
        'config': PREPROCESS_CONFIG,
        'frames_processed': len(results),
        'aggregate_metrics': avg_metrics,
        'results': results,
        'outputs': {
            'comparison_grid': str(grid_path.relative_to(BASE_DIR)),
        }
    }
    
    manifest_out = OUTPUT_DIR / "preprocess_manifest.json"
    with open(manifest_out, 'w') as f:
        json.dump(run_manifest, f, indent=2)
    print(f"\nManifest saved: {manifest_out}")
    
    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Frames processed: {len(results)}")
    if avg_metrics:
        print(f"Avg edge clarity: {avg_metrics['edge_clarity_avg']:.0f}")
        print(f"Avg contrast improvement: {avg_metrics['contrast_improvement_avg']:+.1f}")
        print(f"Avg glare reduction: {avg_metrics['glare_reduction_avg']:+.2f}%")
    print()
    print(f"Outputs saved to: {OUTPUT_DIR}")
    print("Done!")


def create_comparison_grid(
    images: list,
    max_cols: int = 3,
    thumb_height: int = 300
) -> np.ndarray:
    """Create a grid of comparison images."""
    if not images:
        return np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Calculate thumbnail dimensions
    first_img = images[0][1]
    h, w = first_img.shape[:2]
    scale = thumb_height / h
    thumb_w = int(w * scale)
    thumb_h = thumb_height
    
    # Calculate grid
    n_images = len(images)
    cols = min(n_images, max_cols)
    rows = (n_images + cols - 1) // cols
    
    # Create output
    grid_h = rows * (thumb_h + 30)
    grid_w = cols * thumb_w
    grid = np.zeros((grid_h, grid_w, 3), dtype=np.uint8)
    
    for idx, (frame_id, img) in enumerate(images):
        row = idx // cols
        col = idx % cols
        
        # Resize
        thumb = cv2.resize(img, (thumb_w, thumb_h))
        
        # Position
        y = row * (thumb_h + 30)
        x = col * thumb_w
        
        grid[y:y+thumb_h, x:x+thumb_w] = thumb
        
        # Label
        cv2.putText(grid, frame_id, (x + 5, y + thumb_h + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    return grid


if __name__ == "__main__":
    main()
