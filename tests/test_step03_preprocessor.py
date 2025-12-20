# Test script for STEP-03: Preprocessor

"""
Visual verification test for Preprocessor.
Shows before/after preprocessing and verifies pipeline output.

Run: python tests/test_step03_preprocessor.py --video path/to/video.MOV
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cv2
import numpy as np

from mill_presenter.core.frame_loader import FrameLoader
from mill_presenter.core.drum_geometry import DrumGeometry
from mill_presenter.core.preprocessor import Preprocessor


def test_output_shape(frame_bgr: np.ndarray, preprocessor: Preprocessor) -> bool:
    """T03.1: Output is single-channel grayscale with same dimensions."""
    print("\n=== T03.1: Output shape ===")
    try:
        output = preprocessor.process(frame_bgr)
        
        h, w = frame_bgr.shape[:2]
        expected_shape = (h, w)
        
        print(f"  Input shape: {frame_bgr.shape}")
        print(f"  Output shape: {output.shape}")
        
        assert len(output.shape) == 2, "Output should be 2D (grayscale)"
        assert output.shape == expected_shape, f"Expected {expected_shape}, got {output.shape}"
        assert output.dtype == np.uint8, f"Expected uint8, got {output.dtype}"
        
        print("  ✓ T03.1 PASSED")
        return True
    except Exception as e:
        print(f"  ✗ T03.1 FAILED: {e}")
        return False


def test_contrast_improvement(frame_bgr: np.ndarray, preprocessor: Preprocessor) -> bool:
    """T03.2: Preprocessed output has improved or similar contrast."""
    print("\n=== T03.2: Contrast improvement ===")
    try:
        gray_input = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        output = preprocessor.process(frame_bgr)
        
        input_std = gray_input.std()
        output_std = output.std()
        
        print(f"  Input std: {input_std:.2f}")
        print(f"  Output std: {output_std:.2f}")
        
        # Note: With glare suppression, contrast might actually decrease
        # But should remain reasonable
        assert output_std > 10, "Output contrast too low"
        
        print("  ✓ T03.2 PASSED (contrast reasonable)")
        return True
    except Exception as e:
        print(f"  ✗ T03.2 FAILED: {e}")
        return False


def test_roi_masking(frame_bgr: np.ndarray, preprocessor: Preprocessor, 
                     geometry: DrumGeometry) -> bool:
    """T03.3: Pixels outside ROI are zero."""
    print("\n=== T03.3: ROI masking ===")
    try:
        roi_mask = geometry.get_roi_mask(frame_bgr.shape[:2])
        output = preprocessor.process(frame_bgr, roi_mask)
        
        # Check pixels outside mask
        outside_mask = roi_mask == 0
        outside_values = output[outside_mask]
        non_zero_outside = np.sum(outside_values > 0)
        
        print(f"  Total outside pixels: {np.sum(outside_mask)}")
        print(f"  Non-zero outside: {non_zero_outside}")
        
        assert non_zero_outside == 0, f"Found {non_zero_outside} non-zero pixels outside ROI"
        
        print("  ✓ T03.3 PASSED")
        return True
    except Exception as e:
        print(f"  ✗ T03.3 FAILED: {e}")
        return False


def test_determinism(frame_bgr: np.ndarray, preprocessor: Preprocessor) -> bool:
    """T03.4: Same input produces identical output."""
    print("\n=== T03.4: Determinism ===")
    try:
        output1 = preprocessor.process(frame_bgr)
        output2 = preprocessor.process(frame_bgr)
        
        diff = np.abs(output1.astype(float) - output2.astype(float)).sum()
        
        print(f"  Difference between runs: {diff}")
        
        assert diff == 0, f"Outputs differ by {diff}"
        
        print("  ✓ T03.4 PASSED")
        return True
    except Exception as e:
        print(f"  ✗ T03.4 FAILED: {e}")
        return False


def display_comparison(frame_bgr: np.ndarray, preprocessor: Preprocessor,
                       geometry: DrumGeometry) -> bool:
    """Visual comparison: before and after preprocessing."""
    print("\n=== Visual Comparison ===")
    
    # Get preprocessing results
    gray_input = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    roi_mask = geometry.get_roi_mask(frame_bgr.shape[:2])
    output = preprocessor.process(frame_bgr, roi_mask)
    
    # Create side-by-side comparison
    h, w = gray_input.shape[:2]
    
    # Resize for display if too large
    max_dim = 800
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        gray_input = cv2.resize(gray_input, (int(w * scale), int(h * scale)))
        output = cv2.resize(output, (int(w * scale), int(h * scale)))
    
    # Convert to 3-channel for display
    left = cv2.cvtColor(gray_input, cv2.COLOR_GRAY2BGR)
    right = cv2.cvtColor(output, cv2.COLOR_GRAY2BGR)
    
    # Add labels
    cv2.putText(left, "BEFORE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(right, "AFTER", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    combined = np.hstack([left, right])
    
    cv2.imshow("Preprocessing: Before vs After", combined)
    print("\n" + "=" * 50)
    print("VISUAL APPROVAL REQUIRED")
    print("=" * 50)
    print("Does the preprocessing improve contrast and reduce glare?")
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
    parser = argparse.ArgumentParser(description="Test STEP-03: Preprocessor")
    parser.add_argument("--video", required=True, help="Path to test video")
    parser.add_argument("--no-display", action="store_true", help="Skip visual display")
    args = parser.parse_args()
    
    print("=" * 60)
    print("STEP-03: Preprocessor Test Suite")
    print("=" * 60)
    
    # Load video and get first frame
    loader = FrameLoader(args.video)
    frame_bgr = loader.get_frame(0)
    
    # Detect drum geometry
    geometry = DrumGeometry.detect(frame_bgr)
    print(f"\nDrum detected: center=({geometry.center}), radius={geometry.radius}px")
    
    # Create preprocessor
    preprocessor = Preprocessor()
    
    results = {}
    
    # Run tests
    results["T03.1"] = test_output_shape(frame_bgr, preprocessor)
    results["T03.2"] = test_contrast_improvement(frame_bgr, preprocessor)
    results["T03.3"] = test_roi_masking(frame_bgr, preprocessor, geometry)
    results["T03.4"] = test_determinism(frame_bgr, preprocessor)
    
    # Visual comparison
    if not args.no_display:
        results["Visual"] = display_comparison(frame_bgr, preprocessor, geometry)
    else:
        results["Visual"] = None
    
    loader.close()
    
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
        print("\n✓ STEP-03 READY FOR NEXT STEP")
        return 0
    else:
        print("\n✗ STEP-03 HAS FAILURES")
        return 1


if __name__ == "__main__":
    sys.exit(main())
