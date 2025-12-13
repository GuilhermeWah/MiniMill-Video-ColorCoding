"""
STEP_05 Test Script: Confidence Scoring

This script:
1. Loads detection results from STEP_04
2. Scores each detection using confidence features
3. Generates confidence-colored overlays
4. Produces statistics on confidence distribution
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

from config import CONFIDENCE_CONFIG, DETECTION_BEAD_CONFIG
from confidence import (
    score_detections, 
    create_confidence_overlay,
    imread_unicode,
    imwrite_unicode,
    ScoredDetection
)


def main():
    """Run confidence scoring on all golden frames."""
    
    project_root = Path(__file__).parent.parent
    golden_dir = project_root / "data" / "golden_frames"
    detection_dir = project_root / "output" / "detection_test"
    output_dir = project_root / "output" / "confidence_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load golden manifest
    manifest_path = golden_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: Golden manifest not found: {manifest_path}")
        return
    
    with open(manifest_path) as f:
        golden_manifest = json.load(f)
    
    print("=" * 60)
    print("STEP_05: Confidence Scoring Test")
    print("=" * 60)
    print(f"\nUsing CONFIDENCE_CONFIG:")
    for k, v in CONFIDENCE_CONFIG.items():
        print(f"  {k}: {v}")
    print()
    
    results = []
    all_confidences = []
    
    for entry in golden_manifest["frames"]:
        video_full = entry["video"]
        video_name = Path(video_full).stem  # Remove .MOV extension
        frame_idx = entry["frame_idx"]
        raw_path = golden_dir / entry["files"]["raw"]
        
        print(f"\nProcessing: {video_name} frame {frame_idx}")
        
        # Load detection results
        det_json_name = f"{video_name}_frame_{frame_idx}_candidates.json"
        det_json_path = detection_dir / det_json_name
        
        if not det_json_path.exists():
            print(f"  SKIP: Detection file not found: {det_json_path}")
            continue
        
        with open(det_json_path) as f:
            det_data = json.load(f)
        
        candidates = det_data["candidates"]
        drum_radius_px = det_data["params_used"]["drum_radius_px"]
        
        print(f"  Loaded {len(candidates)} candidates")
        
        # Load raw frame
        frame = imread_unicode(raw_path)
        if frame is None:
            print(f"  ERROR: Could not load frame: {raw_path}")
            continue
        
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Score detections
        scored = score_detections(gray, candidates, drum_radius_px, CONFIDENCE_CONFIG)
        
        # Collect statistics
        confidences = [d.conf for d in scored]
        all_confidences.extend(confidences)
        
        high_conf = sum(1 for c in confidences if c >= 0.7)
        med_conf = sum(1 for c in confidences if 0.4 <= c < 0.7)
        low_conf = sum(1 for c in confidences if c < 0.4)
        
        if confidences:
            avg_conf = np.mean(confidences)
            std_conf = np.std(confidences)
            min_conf = np.min(confidences)
            max_conf = np.max(confidences)
        else:
            avg_conf = std_conf = min_conf = max_conf = 0.0
        
        print(f"  Confidence stats:")
        print(f"    High (>=0.7): {high_conf}")
        print(f"    Med (0.4-0.7): {med_conf}")
        print(f"    Low (<0.4): {low_conf}")
        print(f"    Mean: {avg_conf:.3f}, Std: {std_conf:.3f}")
        print(f"    Range: [{min_conf:.3f}, {max_conf:.3f}]")
        
        # Create overlay
        overlay = create_confidence_overlay(frame, scored)
        
        # Save overlay
        overlay_path = output_dir / f"{video_name}_frame_{frame_idx}_confidence.png"
        imwrite_unicode(overlay_path, overlay)
        print(f"  Saved: {overlay_path.name}")
        
        # Save scored detections JSON
        scored_data = {
            "video": video_name,
            "frame_idx": frame_idx,
            "total_candidates": len(scored),
            "high_confidence": high_conf,
            "medium_confidence": med_conf,
            "low_confidence": low_conf,
            "mean_confidence": round(avg_conf, 4),
            "std_confidence": round(std_conf, 4),
            "config_used": CONFIDENCE_CONFIG,
            "detections": [d.to_dict() for d in scored]
        }
        
        json_path = output_dir / f"{video_name}_frame_{frame_idx}_scored.json"
        with open(json_path, 'w') as f:
            json.dump(scored_data, f, indent=2)
        
        results.append({
            "video": video_name,
            "frame_idx": frame_idx,
            "total": len(scored),
            "high": high_conf,
            "med": med_conf,
            "low": low_conf,
            "mean": round(avg_conf, 4),
            "std": round(std_conf, 4),
            "overlay_path": str(overlay_path.relative_to(project_root)),
            "json_path": str(json_path.relative_to(project_root))
        })
    
    # Overall summary
    print("\n" + "=" * 60)
    print("OVERALL SUMMARY")
    print("=" * 60)
    
    if all_confidences:
        print(f"\nTotal detections scored: {len(all_confidences)}")
        print(f"Global mean confidence: {np.mean(all_confidences):.4f}")
        print(f"Global std confidence: {np.std(all_confidences):.4f}")
        print(f"Global range: [{np.min(all_confidences):.4f}, {np.max(all_confidences):.4f}]")
        
        # Confidence distribution
        bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
        hist, _ = np.histogram(all_confidences, bins=bins)
        print(f"\nConfidence distribution:")
        for i in range(len(bins)-1):
            pct = 100 * hist[i] / len(all_confidences)
            print(f"  [{bins[i]:.1f} - {bins[i+1]:.1f}): {hist[i]:5d} ({pct:5.1f}%)")
    
    # Per-video summary
    print("\nPer-video summary:")
    videos = set(r["video"] for r in results)
    for video in sorted(videos):
        video_results = [r for r in results if r["video"] == video]
        total = sum(r["total"] for r in video_results)
        high = sum(r["high"] for r in video_results)
        med = sum(r["med"] for r in video_results)
        low = sum(r["low"] for r in video_results)
        avg_mean = np.mean([r["mean"] for r in video_results])
        print(f"  {video}:")
        print(f"    Total: {total}, High: {high}, Med: {med}, Low: {low}")
        print(f"    Avg mean confidence: {avg_mean:.3f}")
    
    # Save manifest
    manifest = {
        "step": "STEP_05",
        "description": "Confidence scoring results",
        "timestamp": datetime.now().isoformat(),
        "config": CONFIDENCE_CONFIG,
        "global_stats": {
            "total_scored": len(all_confidences),
            "mean": round(np.mean(all_confidences), 4) if all_confidences else 0,
            "std": round(np.std(all_confidences), 4) if all_confidences else 0,
            "min": round(np.min(all_confidences), 4) if all_confidences else 0,
            "max": round(np.max(all_confidences), 4) if all_confidences else 0
        },
        "frames": results
    }
    
    manifest_path = output_dir / "confidence_manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved: {manifest_path}")
    
    print("\n" + "=" * 60)
    print("STEP_05 Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
