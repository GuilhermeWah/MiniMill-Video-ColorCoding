import pytest
from unittest.mock import MagicMock, patch, mock_open
import yaml

def test_save_config_writes_to_file(qapp):
    from mill_presenter.ui.main_window import MainWindow
    
    config = {'calibration': {'px_per_mm': 10.0}}
    config_path = "dummy_config.yaml"
    
    # Mock dependencies
    frame_loader = MagicMock()
    frame_loader.total_frames = 100
    results_cache = MagicMock()
    
    # Mock open
    m_open = mock_open()
    
    with patch("builtins.open", m_open):
        with patch("yaml.dump") as mock_yaml_dump:
            window = MainWindow(config, frame_loader, results_cache, config_path=config_path)
            window.save_config()
            
            m_open.assert_called_with(config_path, "w", encoding="utf-8")
            mock_yaml_dump.assert_called_with(config, m_open(), default_flow_style=False)

def test_calibration_saves_config(qapp, playback_controller_patch):
    from mill_presenter.ui.main_window import MainWindow
    
    config = {'calibration': {'px_per_mm': None}}
    config_path = "dummy_config.yaml"
    frame_loader = MagicMock()
    frame_loader.total_frames = 100
    results_cache = MagicMock()
    
    _, controller_instance = playback_controller_patch
    
    window = MainWindow(config, frame_loader, results_cache, config_path=config_path)
    window.save_config = MagicMock()
    
    # Simulate successful calibration
    window.calibration_controller.points = [(0,0), (10,0)]
    window.calibration_controller.set_known_distance(1.0)
    
    # Manually trigger the apply logic that happens in _on_video_clicked
    # But wait, _on_video_clicked calls calibration_controller.apply() which updates config
    # Then MainWindow should call save_config()
    
    # Let's simulate the flow in _on_video_clicked
    with patch('PyQt6.QtWidgets.QInputDialog.getDouble', return_value=(1.0, True)):
        with patch('PyQt6.QtWidgets.QMessageBox.information'):
             # Simulate 2nd click
            window.calibration_controller.points = [(0,0)] # 1 point already
            window.calibration_controller.is_active = True
            window._on_video_clicked(10, 0)
            
            assert config['calibration']['px_per_mm'] == 10.0
            window.save_config.assert_called_once()
