"""Simple test runner that writes results to a file."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Must create QApplication before any Qt widgets
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

# Run tests and capture output
import io
from contextlib import redirect_stdout, redirect_stderr

output = io.StringIO()

with redirect_stdout(output), redirect_stderr(output):
    try:
        from mill_presenter.ui.calibration_controller import CalibrationController
        
        results = []
        
        # Test 1: starts_inactive
        c = CalibrationController()
        results.append(("starts_inactive", c.is_active == False))
        
        # Test 2: start_activates
        c = CalibrationController()
        c.start()
        results.append(("start_activates", c.is_active == True))
        
        # Test 3: click_when_inactive
        c = CalibrationController()
        result = c.handle_click(100, 100)
        results.append(("click_when_inactive_returns_false", result == False))
        
        # Test 4: first_click_adds_point
        c = CalibrationController()
        c.start()
        c.handle_click(100, 100)
        results.append(("first_click_adds_point", len(c.points) == 1))
        
        # Test 5: second_click_adds_point
        c = CalibrationController()
        c.start()
        c.handle_click(100, 100)
        c.handle_click(200, 200)
        results.append(("second_click_adds_point", len(c.points) == 2))
        
        # Test 6: third_click_ignored
        c = CalibrationController()
        c.start()
        c.handle_click(100, 100)
        c.handle_click(200, 200)
        c.handle_click(300, 300)
        results.append(("third_click_ignored", len(c.points) == 2))
        
        # Test 7: horizontal_distance
        c = CalibrationController()
        c._points = [(0, 0), (100, 0)]
        results.append(("horizontal_distance", c._calculate_pixel_distance() == 100.0))
        
        # Test 8: diagonal_distance (3-4-5 triangle)
        c = CalibrationController()
        c._points = [(0, 0), (30, 40)]
        results.append(("diagonal_distance", c._calculate_pixel_distance() == 50.0))
        
        # Test 9: cancel_clears_points
        c = CalibrationController()
        c.start()
        c._points = [(100, 100), (200, 200)]
        c.cancel()
        results.append(("cancel_clears_points", len(c.points) == 0))
        
        # Test 10: cancel_deactivates
        c = CalibrationController()
        c.start()
        c.cancel()
        results.append(("cancel_deactivates", c.is_active == False))
        
        # Print results
        passed = sum(1 for _, r in results if r)
        failed = sum(1 for _, r in results if not r)
        
        print(f"\n{'='*50}")
        print(f"TEST RESULTS: {passed} passed, {failed} failed")
        print(f"{'='*50}\n")
        
        for name, result in results:
            status = "PASS" if result else "FAIL"
            print(f"[{status}] {name}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

# Write to file
with open("test_results.txt", "w") as f:
    f.write(output.getvalue())

# Also print to console
print(output.getvalue())
