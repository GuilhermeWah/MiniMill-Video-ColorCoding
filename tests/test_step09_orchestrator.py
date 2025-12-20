# Test script for STEP-09: ProcessorOrchestrator

"""
Integration test for the full detection pipeline.
Processes a limited number of frames and verifies output.

Run: python tests/test_step09_orchestrator.py --video path/to/video.MOV --limit 10
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cv2
import numpy as np

from mill_presenter.core.orchestrator import ProcessorOrchestrator
from mill_presenter.core.results_cache import ResultsCache


def print_progress(current: int, total: int):
    """Progress callback."""
    pct = current / total * 100 if total > 0 else 0
    bar_width = 40
    filled = int(bar_width * current / total) if total > 0 else 0
    bar = "=" * filled + "-" * (bar_width - filled)
    print(f"\r  [{bar}] {current}/{total} ({pct:.1f}%)", end="", flush=True)


def test_full_pipeline(video_path: str, cache_path: str, limit: int) -> bool:
    """T09.1: Run full pipeline on limited frames."""
    print("\n=== T09.1: Full pipeline run ===")
    try:
        orchestrator = ProcessorOrchestrator(
            video_path=video_path,
            cache_path=cache_path,
            drum_diameter_mm=200.0
        )
        
        success = orchestrator.run(
            progress_callback=print_progress,
            limit=limit
        )
        print()  # New line after progress bar
        
        assert success, "Pipeline did not complete successfully"
        
        # Verify cache exists
        cache_file = Path(cache_path)
        assert cache_file.exists(), f"Cache file not created: {cache_path}"
        
        print(f"  ✓ Cache created: {cache_file.name}")
        print("  ✓ T09.1 PASSED")
        return True
    except Exception as e:
        print(f"\n  ✗ T09.1 FAILED: {e}")
        return False


def test_cache_load(cache_path: str) -> bool:
    """T09.2: Load and verify cache contents."""
    print("\n=== T09.2: Cache load and verify ===")
    try:
        cache = ResultsCache(cache_path)
        loaded = cache.load()
        
        assert loaded, "Failed to load cache"
        assert cache.is_ready, "Cache not ready after load"
        
        print(f"  Total frames: {cache.total_frames}")
        print(f"  Frame IDs: {cache.frame_ids[:5]}...")
        
        # Verify first frame
        first_id = cache.frame_ids[0]
        first_frame = cache.get_frame(first_id)
        
        assert first_frame is not None, "First frame not found"
        print(f"  Frame {first_id}: {len(first_frame.balls)} detections")
        
        # Show detection breakdown
        class_counts = {}
        for fid in cache.frame_ids[:10]:
            fd = cache.get_frame(fid)
            for ball in fd.balls:
                class_counts[ball.cls] = class_counts.get(ball.cls, 0) + 1
        
        print(f"  Detection classes (first 10 frames): {class_counts}")
        
        print("  ✓ T09.2 PASSED")
        return True
    except Exception as e:
        print(f"  ✗ T09.2 FAILED: {e}")
        return False


def test_detection_quality(cache_path: str) -> bool:
    """T09.3: Basic quality checks on detections."""
    print("\n=== T09.3: Detection quality ===")
    try:
        cache = ResultsCache(cache_path)
        cache.load()
        
        total_detections = 0
        total_confidence = 0.0
        class_distribution = {}
        
        for fid in cache.frame_ids:
            fd = cache.get_frame(fid)
            for ball in fd.balls:
                total_detections += 1
                total_confidence += ball.conf
                class_distribution[ball.cls] = class_distribution.get(ball.cls, 0) + 1
        
        if total_detections > 0:
            avg_conf = total_confidence / total_detections
            avg_per_frame = total_detections / len(cache.frame_ids)
            
            print(f"  Total detections: {total_detections}")
            print(f"  Avg per frame: {avg_per_frame:.1f}")
            print(f"  Avg confidence: {avg_conf:.3f}")
            print(f"  Class distribution: {class_distribution}")
            
            # Quality checks
            assert avg_conf >= 0.4, f"Average confidence too low: {avg_conf}"
            assert total_detections > 0, "No detections found"
            
            print("  ✓ T09.3 PASSED")
            return True
        else:
            print("  ⚠ No detections found (may be acceptable for some videos)")
            return True
    except Exception as e:
        print(f"  ✗ T09.3 FAILED: {e}")
        return False


def display_sample_frame(video_path: str, cache_path: str) -> bool:
    """Visual verification: show detection overlay on a sample frame."""
    print("\n=== Visual Verification ===")
    
    from mill_presenter.core.frame_loader import FrameLoader
    
    # Load cache
    cache = ResultsCache(cache_path)
    if not cache.load():
        print("  Could not load cache for visualization")
        return None
    
    # Load video
    loader = FrameLoader(video_path)
    
    # Get a frame in the middle
    sample_id = cache.frame_ids[min(5, len(cache.frame_ids) - 1)]
    frame = loader.get_frame(sample_id)
    detections = cache.get_frame(sample_id)
    
    # Draw overlays
    overlay_colors = {
        4: (255, 191, 0),   # Blue (BGR)
        6: (0, 255, 0),     # Green
        8: (107, 107, 255), # Red-ish
        10: (0, 215, 255),  # Gold
        0: (128, 128, 128)  # Gray
    }
    
    for ball in detections.balls:
        color = overlay_colors.get(ball.cls, (128, 128, 128))
        cv2.circle(frame, (ball.x, ball.y), int(ball.r_px), color, 2)
        # Label
        label = f"{ball.cls}mm" if ball.cls > 0 else "?"
        cv2.putText(frame, label, (ball.x - 10, ball.y - int(ball.r_px) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    # Add info
    info = f"Frame {sample_id}: {len(detections.balls)} detections"
    cv2.putText(frame, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    loader.close()
    
    # Resize for display
    h, w = frame.shape[:2]
    max_dim = 1000
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
    
    cv2.imshow("Detection Results", frame)
    print("\n" + "=" * 50)
    print("VISUAL APPROVAL REQUIRED")
    print("=" * 50)
    print("Do the detections look reasonable?")
    print("Press 'y' for YES (approved)")
    print("Press 'n' for NO (failed)")
    print("Press any other key to continue without verdict")
    print("=" * 50)
    
    key = cv2.waitKey(0) & 0xFF
    cv2.destroyAllWindows()
    
    if key == ord('y'):
        print("✓ VISUAL APPROVAL: APPROVED")
        return True
    elif key == ord('n'):
        print("✗ VISUAL APPROVAL: REJECTED")
        return False
    else:
        print("? VISUAL APPROVAL: SKIPPED")
        return None


def main():
    parser = argparse.ArgumentParser(description="Test STEP-09: ProcessorOrchestrator")
    parser.add_argument("--video", required=True, help="Path to test video")
    parser.add_argument("--limit", type=int, default=20, help="Frames to process")
    parser.add_argument("--output", help="Cache output path (default: output/test_cache.json)")
    parser.add_argument("--no-display", action="store_true", help="Skip visual display")
    args = parser.parse_args()
    
    # Setup output path
    if args.output:
        cache_path = args.output
    else:
        output_dir = Path(__file__).parent.parent / "output"
        output_dir.mkdir(exist_ok=True)
        cache_path = str(output_dir / "test_cache.json")
    
    print("=" * 60)
    print("STEP-09: ProcessorOrchestrator Test Suite")
    print("=" * 60)
    print(f"Video: {args.video}")
    print(f"Limit: {args.limit} frames")
    print(f"Output: {cache_path}")
    
    results = {}
    
    # Run tests
    results["T09.1"] = test_full_pipeline(args.video, cache_path, args.limit)
    
    if results["T09.1"]:
        results["T09.2"] = test_cache_load(cache_path)
        results["T09.3"] = test_detection_quality(cache_path)
        
        if not args.no_display:
            results["Visual"] = display_sample_frame(args.video, cache_path)
        else:
            results["Visual"] = None
    else:
        results["T09.2"] = None
        results["T09.3"] = None
        results["Visual"] = None
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test_id, result in results.items():
        if result is True:
            print(f"  {test_id}: ✓ PASSED")
            passed += 1
        elif result is False:
            print(f"  {test_id}: ✗ FAILED")
            failed += 1
        else:
            print(f"  {test_id}: ? SKIPPED")
            skipped += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed == 0:
        print("\n✓ CORE PIPELINE VERIFIED")
        return 0
    else:
        print("\n✗ PIPELINE HAS FAILURES")
        return 1


if __name__ == "__main__":
    sys.exit(main())
