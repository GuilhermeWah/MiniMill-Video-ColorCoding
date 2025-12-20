# Quick validation: Compare detection counts with simplified preprocessing

import sys
sys.path.insert(0, 'c:/new/src')

from mill_presenter.core.frame_loader import FrameLoader
from mill_presenter.core.drum_geometry import DrumGeometry
from mill_presenter.core.preprocessor import Preprocessor
from mill_presenter.core.vision_processor import VisionProcessor
from mill_presenter.core.confidence_scorer import ConfidenceScorer
from mill_presenter.core.detection_filter import DetectionFilter
from mill_presenter.core.classifier import Classifier
from mill_presenter.utils import config
import time

def run_validation(video_path: str, frames_to_test: list):
    """Run detection on specific frames and report counts."""
    
    print(f"\n{'='*60}")
    print(f"VALIDATION: Simplified Preprocessing (Legacy-Compatible)")
    print(f"{'='*60}")
    print(f"Video: {video_path}\n")
    
    # Initialize components
    loader = FrameLoader(video_path)
    cfg = config.CONFIG
    preprocessor = Preprocessor(cfg)
    processor = VisionProcessor(cfg)
    scorer = ConfidenceScorer(cfg)
    filter_ = DetectionFilter(cfg)
    classifier = Classifier()
    
    # Detect drum geometry on first frame
    first_frame = loader.get_frame(0)
    geometry = DrumGeometry.detect(first_frame, 200.0)
    print(f"Drum: center=({geometry.center[0]}, {geometry.center[1]}), r={geometry.radius}px")
    print(f"Calibration: {geometry.px_per_mm:.3f} px/mm\n")
    
    roi_mask = geometry.get_roi_mask((loader.height, loader.width))
    
    # Process each test frame
    results = []
    total_time = 0
    
    print(f"{'Frame':<8} {'Raw':>8} {'After Filter':>12} {'Time (ms)':>10}")
    print(f"{'-'*8} {'-'*8} {'-'*12} {'-'*10}")
    
    for frame_idx in frames_to_test:
        frame = loader.get_frame(frame_idx)
        
        start = time.time()
        
        # Pipeline
        preprocessed = preprocessor.process(frame, roi_mask)
        candidates = processor.detect(preprocessed, geometry)
        scored = scorer.score(candidates, preprocessed, geometry)
        filtered = filter_.filter(scored, geometry, preprocessed)
        balls = classifier.classify(filtered, geometry.px_per_mm)
        
        elapsed_ms = (time.time() - start) * 1000
        total_time += elapsed_ms
        
        # Count by class
        class_counts = {4: 0, 6: 0, 8: 0, 10: 0}
        for ball in balls:
            if ball.cls in class_counts:
                class_counts[ball.cls] += 1
        
        print(f"{frame_idx:<8} {len(candidates):>8} {len(balls):>12} {elapsed_ms:>10.1f}")
        
        results.append({
            'frame': frame_idx,
            'raw': len(candidates),
            'filtered': len(balls),
            'by_class': class_counts,
            'time_ms': elapsed_ms
        })
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    avg_filtered = sum(r['filtered'] for r in results) / len(results)
    avg_time = total_time / len(results)
    print(f"Average detections after filter: {avg_filtered:.1f}")
    print(f"Average time per frame: {avg_time:.1f} ms")
    print(f"Effective FPS: {1000/avg_time:.1f}")
    
    # Class distribution (last frame)
    print(f"\nClass distribution (frame {frames_to_test[-1]}):")
    for cls in [4, 6, 8, 10]:
        print(f"  {cls}mm: {results[-1]['by_class'][cls]}")
    
    loader.close()
    return results


if __name__ == "__main__":
    video = "c:/new/videos_sample/DSC_3310.MOV"
    # Test same frames as previous validation
    test_frames = [0, 100, 200]
    
    run_validation(video, test_frames)
