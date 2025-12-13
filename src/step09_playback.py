"""
STEP_09 Test Script: Visualization & Playback

This script demonstrates the cached playback system:
1. Builds a detection cache from classified results
2. Opens video with real-time overlay rendering
3. Tests playback performance (target: 30-60 FPS)

Controls:
- SPACE: Play/Pause
- LEFT/RIGHT: Step frame
- Q/ESC: Quit
- 1-4: Toggle class visibility
- +/-: Adjust confidence threshold
"""

import json
import sys
import time
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import SIZE_CONFIG
from cache import (
    DetectionCacheWriter,
    DetectionCacheReader,
    get_cache_path,
    CachedDetection
)
from playback import PlaybackRenderer, PlaybackConfig, create_playback_config_from_size_config


def build_cache_from_classified_results(project_root: Path, video_name: str) -> str:
    """Build detection cache from STEP_07 classification results."""
    
    classify_dir = project_root / "output" / "classify_test"
    cache_dir = project_root / "cache" / "detections"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all classified JSON files for this video
    json_files = sorted(classify_dir.glob(f"{video_name}_frame_*_classified.json"))
    
    if not json_files:
        print(f"No classified results found for {video_name}")
        return None
    
    # Load first file to get metadata
    with open(json_files[0]) as f:
        first_data = json.load(f)
    
    px_per_mm = first_data["px_per_mm"]
    drum_radius = first_data["drum_radius_px"]
    
    # Load geometry for drum center
    import hashlib
    video_filename = f"{video_name}.MOV"
    hash_part = hashlib.md5(video_filename.encode()).hexdigest()[:8]
    geom_path = project_root / "cache" / "geometry" / f"{video_name}_{hash_part}.json"
    
    if geom_path.exists():
        with open(geom_path) as f:
            geom = json.load(f)
        drum_center = (geom["drum_center_x_px"], geom["drum_center_y_px"])
    else:
        drum_center = (0, 0)
    
    # Estimate video properties from geometry
    # We'll use placeholder values since we're building from golden frames
    width = drum_center[0] * 2 if drum_center[0] > 0 else 1920
    height = drum_center[1] * 2 if drum_center[1] > 0 else 1080
    fps = 30.0
    
    # Create cache writer
    writer = DetectionCacheWriter(
        video_path=f"{video_name}.MOV",
        fps=fps,
        width=width,
        height=height,
        px_per_mm=px_per_mm,
        drum_center=drum_center,
        drum_radius=drum_radius,
        config=SIZE_CONFIG
    )
    
    # Add each frame
    for json_path in json_files:
        with open(json_path) as f:
            data = json.load(f)
        
        frame_idx = data["frame_idx"]
        detections = data["detections"]
        
        writer.add_frame(frame_idx, detections)
    
    # Save cache
    cache_path = cache_dir / f"{video_name}_detections.json"
    writer.save(str(cache_path))
    
    print(f"Cache built: {cache_path.name} ({len(json_files)} frames)")
    return str(cache_path)


def test_playback_with_golden_frames(project_root: Path, video_name: str):
    """Test playback rendering with golden frames (no video file needed)."""
    
    golden_dir = project_root / "data" / "golden_frames"
    cache_dir = project_root / "cache" / "detections"
    cache_path = cache_dir / f"{video_name}_detections.json"
    
    if not cache_path.exists():
        print(f"Cache not found: {cache_path}")
        return
    
    # Load cache
    reader = DetectionCacheReader(str(cache_path))
    print(f"\nLoaded cache: {reader.video_name}")
    print(f"  Cached frames: {len(reader.cached_frame_indices())}")
    print(f"  px_per_mm: {reader.px_per_mm}")
    print(f"  Drum: center={reader.drum_center}, radius={reader.drum_radius}")
    
    # Create renderer with config
    playback_config = create_playback_config_from_size_config(SIZE_CONFIG)
    renderer = PlaybackRenderer(playback_config)
    
    # Load golden manifest to get frame paths
    manifest_path = golden_dir / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    # Filter frames for this video
    video_frames = [
        e for e in manifest["frames"] 
        if Path(e["video"]).stem == video_name
    ]
    
    if not video_frames:
        print(f"No golden frames found for {video_name}")
        return
    
    # Performance tracking
    render_times = []
    
    # Test rendering each frame
    for entry in video_frames:
        frame_idx = entry["frame_idx"]
        raw_path = golden_dir / entry["files"]["raw"]
        
        if not raw_path.exists():
            continue
        
        # Load frame
        frame = cv2.imdecode(
            np.frombuffer(open(raw_path, 'rb').read(), np.uint8),
            cv2.IMREAD_COLOR
        )
        
        if frame is None:
            continue
        
        # Get cached detections
        detections = reader.get_detections(frame_idx)
        stats = reader.get_stats(frame_idx)
        
        # Time the render
        start = time.perf_counter()
        
        rendered = renderer.render_frame(
            frame,
            detections,
            drum_center=reader.drum_center,
            drum_radius=reader.drum_radius,
            stats=stats
        )
        
        render_time = (time.perf_counter() - start) * 1000  # ms
        render_times.append(render_time)
        
        print(f"  Frame {frame_idx}: {len(detections)} detections, render={render_time:.2f}ms")
    
    # Performance summary
    if render_times:
        avg_time = sum(render_times) / len(render_times)
        max_time = max(render_times)
        theoretical_fps = 1000 / avg_time if avg_time > 0 else 0
        
        print(f"\n  Render Performance:")
        print(f"    Average: {avg_time:.2f}ms per frame")
        print(f"    Max: {max_time:.2f}ms")
        print(f"    Theoretical FPS: {theoretical_fps:.1f}")
        print(f"    Target (30-60 FPS): {'PASS' if theoretical_fps >= 30 else 'FAIL (optimize needed)'}")


def interactive_playback_demo(project_root: Path, video_name: str):
    """Interactive demo showing playback controls (requires golden frames)."""
    
    golden_dir = project_root / "data" / "golden_frames"
    cache_dir = project_root / "cache" / "detections"
    cache_path = cache_dir / f"{video_name}_detections.json"
    
    if not cache_path.exists():
        print(f"Cache not found: {cache_path}")
        return
    
    # Load cache
    reader = DetectionCacheReader(str(cache_path))
    
    # Create renderer
    config = create_playback_config_from_size_config(SIZE_CONFIG)
    renderer = PlaybackRenderer(config)
    
    # Load golden manifest
    manifest_path = golden_dir / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    # Get frames for this video
    video_frames = [
        e for e in manifest["frames"] 
        if Path(e["video"]).stem == video_name
    ]
    
    if not video_frames:
        return
    
    # Preload all frames
    frames = []
    for entry in video_frames:
        raw_path = golden_dir / entry["files"]["raw"]
        if raw_path.exists():
            frame = cv2.imdecode(
                np.frombuffer(open(raw_path, 'rb').read(), np.uint8),
                cv2.IMREAD_COLOR
            )
            if frame is not None:
                frames.append((entry["frame_idx"], frame))
    
    if not frames:
        print("No frames loaded")
        return
    
    print(f"\n{'='*60}")
    print("Interactive Playback Demo")
    print("=" * 60)
    print("Controls:")
    print("  SPACE    : Play/Pause")
    print("  ←/→      : Previous/Next frame")
    print("  1/2/3/4  : Toggle 4mm/6mm/8mm/10mm visibility")
    print("  +/-      : Adjust confidence threshold")
    print("  S        : Toggle stats overlay")
    print("  L        : Toggle legend")
    print("  Q/ESC    : Quit")
    print("=" * 60)
    
    current_idx = 0
    playing = False
    
    window_name = f"MillPresenter Playback - {video_name}"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    while True:
        frame_idx, frame = frames[current_idx]
        
        # Get cached detections
        detections = reader.get_detections(frame_idx)
        stats = reader.get_stats(frame_idx)
        
        # Render
        rendered = renderer.render_frame(
            frame,
            detections,
            drum_center=reader.drum_center,
            drum_radius=reader.drum_radius,
            stats=stats
        )
        
        # Add frame info
        info = f"Frame {current_idx+1}/{len(frames)} | Idx: {frame_idx} | Conf >= {config.min_confidence:.2f}"
        cv2.putText(rendered, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.imshow(window_name, rendered)
        
        # Handle input
        wait_time = 33 if playing else 0  # ~30 FPS when playing
        key = cv2.waitKey(wait_time) & 0xFF
        
        if key == ord('q') or key == 27:  # Q or ESC
            break
        elif key == ord(' '):  # Space
            playing = not playing
        elif key == 81 or key == ord('a'):  # Left arrow
            current_idx = max(0, current_idx - 1)
            playing = False
        elif key == 83 or key == ord('d'):  # Right arrow
            current_idx = min(len(frames) - 1, current_idx + 1)
            playing = False
        elif key == ord('1'):
            config.show_4mm = not config.show_4mm
            print(f"4mm: {'ON' if config.show_4mm else 'OFF'}")
        elif key == ord('2'):
            config.show_6mm = not config.show_6mm
            print(f"6mm: {'ON' if config.show_6mm else 'OFF'}")
        elif key == ord('3'):
            config.show_8mm = not config.show_8mm
            print(f"8mm: {'ON' if config.show_8mm else 'OFF'}")
        elif key == ord('4'):
            config.show_10mm = not config.show_10mm
            print(f"10mm: {'ON' if config.show_10mm else 'OFF'}")
        elif key == ord('+') or key == ord('='):
            config.min_confidence = min(1.0, config.min_confidence + 0.05)
            print(f"Confidence threshold: {config.min_confidence:.2f}")
        elif key == ord('-'):
            config.min_confidence = max(0.0, config.min_confidence - 0.05)
            print(f"Confidence threshold: {config.min_confidence:.2f}")
        elif key == ord('s'):
            config.show_stats = not config.show_stats
        elif key == ord('l'):
            config.show_legend = not config.show_legend
        
        # Auto-advance when playing
        if playing:
            current_idx = (current_idx + 1) % len(frames)
    
    cv2.destroyAllWindows()


def main():
    """Run playback tests."""
    
    project_root = Path(__file__).parent.parent
    
    print("=" * 70)
    print("STEP_09: Visualization & Playback Test")
    print("=" * 70)
    
    # Build caches for all videos with classified results
    videos = ["IMG_6535", "IMG_1276", "DSC_3310"]
    
    print("\n1. Building detection caches...")
    for video_name in videos:
        build_cache_from_classified_results(project_root, video_name)
    
    print("\n2. Testing playback performance...")
    for video_name in videos:
        print(f"\n--- {video_name} ---")
        test_playback_with_golden_frames(project_root, video_name)
    
    # Interactive demo with first video that has data
    print("\n3. Interactive playback demo...")
    print("   (Press any key to start, or 'S' to skip)")
    
    key = cv2.waitKey(0) & 0xFF
    if key != ord('s') and key != ord('S'):
        for video_name in videos:
            cache_path = project_root / "cache" / "detections" / f"{video_name}_detections.json"
            if cache_path.exists():
                interactive_playback_demo(project_root, video_name)
                break
    
    print("\n" + "=" * 70)
    print("STEP_09: Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
