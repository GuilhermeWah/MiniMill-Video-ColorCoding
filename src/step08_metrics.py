"""
STEP_08 Test Script: Quality Metrics

This script:
1. Loads classified detections from STEP_07
2. Computes quality metrics per video and aggregate
3. Validates against acceptance criteria
4. Generates quality report
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from metrics import (
    FrameMetrics,
    generate_quality_report,
    generate_aggregate_report,
    QualityReport
)


def main():
    """Run quality metrics on all golden frames."""
    
    project_root = Path(__file__).parent.parent
    golden_dir = project_root / "data" / "golden_frames"
    classify_dir = project_root / "output" / "classify_test"
    output_dir = project_root / "output" / "metrics"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load golden manifest
    manifest_path = golden_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: Golden manifest not found: {manifest_path}")
        return
    
    with open(manifest_path) as f:
        golden_manifest = json.load(f)
    
    print("=" * 70)
    print("STEP_08: Quality Metrics Analysis")
    print("=" * 70)
    
    # Group frames by video
    frames_by_video = {}
    for entry in golden_manifest["frames"]:
        video_full = entry["video"]
        video_name = Path(video_full).stem
        if video_name not in frames_by_video:
            frames_by_video[video_name] = []
        frames_by_video[video_name].append(entry)
    
    all_reports = []
    
    for video_name, entries in frames_by_video.items():
        print(f"\n{'='*60}")
        print(f"Video: {video_name}")
        print("=" * 60)
        
        frame_metrics_list = []
        
        for entry in entries:
            frame_idx = entry["frame_idx"]
            
            # Load classified detections
            json_path = classify_dir / f"{video_name}_frame_{frame_idx}_classified.json"
            if not json_path.exists():
                print(f"  SKIP: {json_path.name} not found")
                continue
            
            with open(json_path) as f:
                data = json.load(f)
            
            detections = data["detections"]
            stats = data["classification_stats"]
            
            # Extract confidence values
            conf_values = [d["conf"] for d in detections]
            
            # Build frame metrics
            fm = FrameMetrics(
                video=video_name,
                frame_idx=frame_idx,
                total_count=stats["total_count"],
                counts_by_class=stats["by_class"],
                confidence_values=conf_values,
                processing_time_ms=0  # Not tracked in this run
            )
            frame_metrics_list.append(fm)
        
        if not frame_metrics_list:
            print(f"  No frame data found for {video_name}")
            continue
        
        # Generate report for this video
        report = generate_quality_report(video_name, frame_metrics_list)
        all_reports.append(report)
        
        # Print summary
        cs = report.count_stability
        sd = report.size_distribution
        cf = report.confidence
        
        print(f"\n  Frames analyzed: {report.n_frames}")
        print(f"  Total detections: {report.total_detections}")
        
        print(f"\n  COUNT STABILITY:")
        print(f"    Mean count: {cs.mean_count:.1f}")
        print(f"    Std dev: {cs.std_count:.1f}")
        print(f"    CV (coefficient of variation): {cs.cv:.3f}")
        print(f"    Range: {cs.min_count} - {cs.max_count}")
        print(f"    Rating: {cs.to_dict()['stability_rating']}")
        
        print(f"\n  SIZE DISTRIBUTION (mean %):")
        for cls in ["4mm", "6mm", "8mm", "10mm", "unknown"]:
            pct = sd.mean_proportions.get(cls, 0) * 100
            std = sd.std_proportions.get(cls, 0) * 100
            print(f"    {cls:8s}: {pct:5.1f}% ± {std:4.1f}%")
        
        print(f"\n  CONFIDENCE DISTRIBUTION:")
        print(f"    Mean: {cf.mean:.3f}")
        print(f"    Median: {cf.median:.3f}")
        print(f"    Std dev: {cf.std:.3f}")
        print(f"    Range: {cf.min_val:.3f} - {cf.max_val:.3f}")
        print(f"    Rating: {cf.to_dict()['distribution_rating']}")
        
        print(f"\n  Confidence Histogram:")
        for bin_name, count in cf.histogram.items():
            bar = "█" * (count // 5)
            print(f"    {bin_name}: {count:4d} {bar}")
        
        # Save per-video report
        video_report_path = output_dir / f"{video_name}_quality_report.json"
        with open(video_report_path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"\n  Saved: {video_report_path.name}")
    
    # Generate aggregate report
    print("\n" + "=" * 70)
    print("AGGREGATE QUALITY METRICS (All Videos)")
    print("=" * 70)
    
    aggregate = generate_aggregate_report(all_reports)
    
    summary = aggregate["aggregate_summary"]
    print(f"\n  Videos analyzed: {summary['total_videos']}")
    print(f"  Total frames: {summary['total_frames']}")
    print(f"  Total detections: {summary['total_detections']}")
    print(f"  Overall count CV: {summary['overall_count_cv']:.3f}")
    print(f"  Stability rating: {summary['count_stability_rating']}")
    
    sd = aggregate["size_distribution"]
    print(f"\n  OVERALL SIZE DISTRIBUTION:")
    for cls in ["4mm", "6mm", "8mm", "10mm", "unknown"]:
        pct = sd["mean_proportions"].get(cls, 0)
        print(f"    {cls:8s}: {pct:5.1f}%")
    
    cf = aggregate["confidence"]
    print(f"\n  OVERALL CONFIDENCE:")
    print(f"    Mean: {cf['mean']:.3f}")
    print(f"    Range: {cf['min']:.3f} - {cf['max']:.3f}")
    print(f"    Rating: {cf['distribution_rating']}")
    
    # Acceptance criteria check
    print("\n" + "=" * 70)
    print("ACCEPTANCE CRITERIA CHECK")
    print("=" * 70)
    
    passed = True
    
    # Check 1: Count CV < 0.35 (Acceptable threshold)
    cv = summary['overall_count_cv']
    cv_pass = cv < 0.35
    print(f"\n  [{'✓' if cv_pass else '✗'}] Count Stability CV < 0.35: {cv:.3f}")
    passed = passed and cv_pass
    
    # Check 2: Confidence range > 0.2 (not collapsed)
    conf_range = cf['max'] - cf['min']
    conf_pass = conf_range > 0.2
    print(f"  [{'✓' if conf_pass else '✗'}] Confidence Range > 0.2: {conf_range:.3f}")
    passed = passed and conf_pass
    
    # Check 3: Unknown class < 10%
    unknown_pct = sd["mean_proportions"].get("unknown", 0)
    unknown_pass = unknown_pct < 10
    print(f"  [{'✓' if unknown_pass else '✗'}] Unknown < 10%: {unknown_pct:.1f}%")
    passed = passed and unknown_pass
    
    # Check 4: Size distribution has no empty classes (except unknown)
    all_classes_present = all(
        sd["mean_proportions"].get(cls, 0) > 1 
        for cls in ["4mm", "6mm", "8mm", "10mm"]
    )
    print(f"  [{'✓' if all_classes_present else '✗'}] All size classes > 1%: {all_classes_present}")
    passed = passed and all_classes_present
    
    print(f"\n  {'='*50}")
    print(f"  OVERALL: {'PASS ✓' if passed else 'FAIL ✗'}")
    print(f"  {'='*50}")
    
    # Save aggregate report
    aggregate_path = output_dir / "aggregate_quality_report.json"
    aggregate["acceptance_check"] = {
        "count_stability_pass": cv_pass,
        "confidence_range_pass": conf_pass,
        "unknown_class_pass": unknown_pass,
        "all_classes_present": all_classes_present,
        "overall_pass": passed
    }
    aggregate["timestamp"] = datetime.now().isoformat()
    
    with open(aggregate_path, 'w') as f:
        json.dump(aggregate, f, indent=2)
    
    print(f"\n  Aggregate report saved: {aggregate_path}")
    print(f"  Per-video reports saved to: {output_dir}")


if __name__ == "__main__":
    main()
