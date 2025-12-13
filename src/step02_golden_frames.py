"""
STEP_02: Golden Frames Lock (Baseline Validation Set)

Extracts and locks a curated set of golden frames from test videos.
Golden frames serve as the immutable baseline for all subsequent pipeline steps.

Outputs:
- data/golden_frames/{video}_frame_{idx}.png (raw frames)
- data/golden_frames/{video}_frame_{idx}_masked.png (ROI-masked)
- data/golden_frames/manifest.json (metadata + SHA256 hashes)
- output/step02_manifest.json (run manifest)
"""

import argparse
import cv2
import hashlib
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import load_geometry_for_video, GEOMETRY_CACHE_DIR
from src.drum import generate_roi_mask, imwrite_unicode


def get_video_info(video_path: str) -> Dict[str, Any]:
    """Get video metadata."""
    cap = cv2.VideoCapture(video_path)
    info = {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    }
    cap.release()
    return info


def compute_strategic_indices(frame_count: int) -> List[int]:
    """
    Compute strategic frame indices for golden frame extraction.
    
    Returns indices at:
    - Frame 0: Start
    - Frame 100: Early operation
    - 25% duration
    - 50% duration
    - 75% duration
    - total - 10: Near end
    """
    indices = [
        0,                              # Start
        min(100, frame_count - 1),      # Early operation
        int(frame_count * 0.25),        # Quarter mark
        int(frame_count * 0.50),        # Midpoint
        int(frame_count * 0.75),        # Three-quarter mark
        max(0, frame_count - 10)        # Near end
    ]
    # Remove duplicates and sort
    indices = sorted(set(indices))
    return indices


def compute_sha256(image_path: str) -> str:
    """Compute SHA256 hash of an image file."""
    sha256 = hashlib.sha256()
    with open(image_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def extract_frame(video_path: str, frame_idx: int) -> Optional[Any]:
    """Extract a single frame from video."""
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()
    return frame if ret else None


def apply_roi_mask(frame: Any, mask: Any) -> Any:
    """Apply ROI mask to frame (black out areas outside ROI)."""
    masked = frame.copy()
    masked[mask == 0] = 0
    return masked


def extract_golden_frames(
    video_path: str,
    output_dir: str,
    config_dir: str,
    cache_dir: str,
    frame_indices: Optional[List[int]] = None
) -> List[Dict[str, Any]]:
    """
    Extract golden frames from a single video.
    
    Returns list of frame metadata dictionaries.
    """
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    video_info = get_video_info(video_path)
    
    print(f"\nProcessing: {video_name}")
    print(f"  Resolution: {video_info['width']}x{video_info['height']}")
    print(f"  Frames: {video_info['frame_count']}")
    
    # Get frame indices
    if frame_indices is None:
        frame_indices = compute_strategic_indices(video_info['frame_count'])
    print(f"  Extracting frames: {frame_indices}")
    
    # Load geometry for this video (need a reference frame first)
    ref_frame = extract_frame(video_path, 0)
    if ref_frame is None:
        print(f"  ERROR: Could not read reference frame")
        return []
    
    geometry, status = load_geometry_for_video(
        video_path=video_path,
        frame=ref_frame,
        config_dir=config_dir,
        cache_dir=cache_dir
    )
    print(f"  Geometry: {status}")
    
    # Generate ROI mask
    frame_shape = ref_frame.shape[:2]
    roi_mask = generate_roi_mask(geometry, frame_shape)
    
    # Get geometry cache filename for reference
    from src.config import get_geometry_cache_path
    geometry_cache_path = get_geometry_cache_path(video_path, cache_dir)
    geometry_cache_name = os.path.basename(geometry_cache_path)
    
    frames_metadata = []
    
    for idx in frame_indices:
        frame = extract_frame(video_path, idx)
        if frame is None:
            print(f"  WARNING: Could not read frame {idx}")
            continue
        
        # Generate filenames
        frame_id = f"{video_name}_frame_{idx}"
        raw_filename = f"{frame_id}.png"
        masked_filename = f"{frame_id}_masked.png"
        
        raw_path = os.path.join(output_dir, raw_filename)
        masked_path = os.path.join(output_dir, masked_filename)
        
        # Save raw frame
        success_raw = imwrite_unicode(raw_path, frame)
        if not success_raw:
            print(f"  ERROR: Failed to write {raw_filename}")
            continue
        
        # Apply mask and save masked frame
        masked_frame = apply_roi_mask(frame, roi_mask)
        success_masked = imwrite_unicode(masked_path, masked_frame)
        if not success_masked:
            print(f"  ERROR: Failed to write {masked_filename}")
            continue
        
        # Compute hashes
        sha256_raw = compute_sha256(raw_path)
        sha256_masked = compute_sha256(masked_path)
        
        # Build metadata
        metadata = {
            "id": frame_id,
            "video": os.path.basename(video_path),
            "frame_idx": idx,
            "resolution": f"{video_info['width']}x{video_info['height']}",
            "sha256": sha256_raw,
            "sha256_masked": sha256_masked,
            "tags": [],  # Tags will be added manually or in future step
            "geometry_cache": geometry_cache_name,
            "files": {
                "raw": raw_filename,
                "masked": masked_filename
            }
        }
        
        frames_metadata.append(metadata)
        print(f"  ✓ Frame {idx}: {sha256_raw[:12]}...")
    
    return frames_metadata


def main():
    parser = argparse.ArgumentParser(
        description="STEP_02: Golden Frames Lock - Extract baseline validation frames"
    )
    parser.add_argument("--videos", nargs="+", required=True,
                        help="Paths to input videos")
    parser.add_argument("--output-dir", default="data/golden_frames",
                        help="Output directory for golden frames")
    parser.add_argument("--config-dir", default="config",
                        help="Config directory")
    parser.add_argument("--cache-dir", default="cache/geometry",
                        help="Geometry cache directory")
    parser.add_argument("--frames", default=None,
                        help="Comma-separated frame indices (default: auto)")
    args = parser.parse_args()
    
    start_time = datetime.now()
    
    # Paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = args.output_dir if os.path.isabs(args.output_dir) else os.path.join(project_root, args.output_dir)
    config_dir = args.config_dir if os.path.isabs(args.config_dir) else os.path.join(project_root, args.config_dir)
    cache_dir = args.cache_dir if os.path.isabs(args.cache_dir) else os.path.join(project_root, args.cache_dir)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Parse frame indices if provided
    frame_indices = None
    if args.frames:
        frame_indices = [int(x) for x in args.frames.split(",")]
    
    # Process all videos
    all_frames_metadata = []
    videos_processed = []
    
    for video_arg in args.videos:
        video_path = video_arg if os.path.isabs(video_arg) else os.path.join(project_root, video_arg)
        
        if not os.path.exists(video_path):
            print(f"WARNING: Video not found: {video_path}")
            continue
        
        frames = extract_golden_frames(
            video_path=video_path,
            output_dir=output_dir,
            config_dir=config_dir,
            cache_dir=cache_dir,
            frame_indices=frame_indices
        )
        
        all_frames_metadata.extend(frames)
        videos_processed.append(os.path.basename(video_path))
    
    # Write golden frames manifest
    end_time = datetime.now()
    
    golden_manifest = {
        "version": "1.0",
        "locked_date": end_time.isoformat(),
        "step_id": "STEP_02",
        "videos": videos_processed,
        "frame_count": len(all_frames_metadata),
        "frames": all_frames_metadata
    }
    
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, 'w') as f:
        json.dump(golden_manifest, f, indent=2)
    
    # Write run manifest
    run_manifest = {
        "step_id": "STEP_02",
        "title": "Golden Frames Lock",
        "timestamp": end_time.isoformat(),
        "duration_sec": (end_time - start_time).total_seconds(),
        "input": {
            "videos": videos_processed,
            "frame_selection": "strategic" if frame_indices is None else "manual"
        },
        "output": {
            "golden_frames_dir": output_dir,
            "manifest": manifest_path,
            "frame_count": len(all_frames_metadata)
        },
        "validation": {
            "determinism": "SHA256 hashes computed for all frames",
            "immutability": "Re-run should produce identical hashes"
        }
    }
    
    run_manifest_path = os.path.join(project_root, "output", "step02_manifest.json")
    os.makedirs(os.path.dirname(run_manifest_path), exist_ok=True)
    with open(run_manifest_path, 'w') as f:
        json.dump(run_manifest, f, indent=2)
    
    # Summary
    print(f"\n{'='*50}")
    print(f"STEP_02 Complete: Golden Frames Lock")
    print(f"{'='*50}")
    print(f"Videos processed: {len(videos_processed)}")
    print(f"Golden frames extracted: {len(all_frames_metadata)}")
    print(f"Duration: {(end_time - start_time).total_seconds():.2f}s")
    print(f"\nArtifacts:")
    print(f"  Golden frames: {output_dir}/")
    print(f"  Manifest: {manifest_path}")
    print(f"  Run manifest: {run_manifest_path}")


if __name__ == "__main__":
    main()
