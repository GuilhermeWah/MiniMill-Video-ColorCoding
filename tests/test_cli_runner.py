import pytest
import subprocess
import sys
import os
import cv2
import numpy as np
import yaml

# ==================================================================================
# TEST SUITE: CLI Runner (Integration Test)
# ==================================================================================
# Purpose:
#   Verify that the 'scripts/run_detection.py' script works as a standalone tool.
#   This is the "Integration Test" that proves Loader + Processor + Cache + Orchestrator
#   all work together to produce a result file.
#
# Criteria for Success:
#   1. Script runs without error (Exit Code 0).
#   2. Produces a 'detections.jsonl' file.
#   3. The output file contains valid JSON data for each frame.
# ==================================================================================

@pytest.fixture
def script_path():
    """Returns the absolute path to the run_detection.py script."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts/run_detection.py'))

@pytest.fixture
def temp_config(tmp_path):
    """Creates a temporary config file."""
    config = {
        'calibration': {'px_per_mm': 15.0},
        'vision': {'hough_param1': 50, 'hough_param2': 30, 'min_dist_px': 15, 'min_circularity': 0.65},
        'bins_mm': [{'label': 4, 'min': 3.0, 'max': 5.0}]
    }
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    return str(config_path)

@pytest.fixture
def temp_video(tmp_path):
    """Creates a temporary 5-frame video."""
    video_path = tmp_path / "integration_test.mp4"
    path_str = str(video_path)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(path_str, fourcc, 30.0, (100, 100))
    
    for i in range(5):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # Draw a white circle (bead)
        cv2.circle(frame, (50, 50), 20, (255, 255, 255), -1)
        out.write(frame)
        
    out.release()
    return path_str

def test_cli_help(script_path):
    """
    Milestone 2: CLI - Verify help command.
    """
    result = subprocess.run(
        [sys.executable, script_path, "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout

def test_cli_full_run(script_path, temp_video, temp_config, tmp_path):
    """
    Milestone 2: CLI - Verify full pipeline execution.
    """
    output_path = tmp_path / "output_detections.jsonl"
    
    # Run the script
    cmd = [
        sys.executable, script_path,
        "--input", temp_video,
        "--output", str(output_path),
        "--config", temp_config
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Check for success
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        
    assert result.returncode == 0, "Script failed to run"
    
    # Check output file
    assert output_path.exists(), "Output file was not created"
    
    with open(output_path, 'r') as f:
        lines = f.readlines()
        
    # Should have 5 lines (one per frame)
    assert len(lines) == 5, f"Expected 5 output lines, got {len(lines)}"
    
    # Check content of first line
    import json
    first_frame = json.loads(lines[0])
    assert first_frame['frame_id'] == 0
    # We drew a circle, so we expect at least one ball
    assert len(first_frame['balls']) > 0
