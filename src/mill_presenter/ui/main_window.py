from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QSlider, 
    QInputDialog, QMessageBox, QStatusBar, QFileDialog, QProgressDialog, 
    QLabel, QComboBox, QDialog, QDialogButtonBox, QSpinBox, QFormLayout, QGroupBox
)
import yaml
import os
import cv2
import numpy as np
from mill_presenter.ui.widgets import VideoWidget
from mill_presenter.ui.playback_controller import PlaybackController
from mill_presenter.ui.calibration_controller import CalibrationController
from mill_presenter.ui.drum_calibration_controller import DrumCalibrationController
from mill_presenter.ui.roi_controller import ROIController
from mill_presenter.core.exporter import VideoExporter
from mill_presenter.core.orchestrator import DetectionThread
from mill_presenter.core.cache import ResultsCache, get_detection_path


class DetectionDialog(QDialog):
    """Dialog for configuring detection parameters before running."""
    
    # Estimated processing speed (frames per second)
    # Conservative estimate: ~5 fps (200ms per frame) - includes decode + CV processing
    # Actual speed varies by hardware and video resolution
    ESTIMATED_FPS = 5.0
    
    def __init__(self, total_frames: int, fps: float, parent=None):
        super().__init__(parent)
        self.total_frames = total_frames
        self.fps = fps
        self.setWindowTitle("Run Detection")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Info group
        info_group = QGroupBox("Video Info")
        info_layout = QFormLayout(info_group)
        total_seconds = total_frames / fps if fps > 0 else 0
        info_layout.addRow("Total Frames:", QLabel(str(total_frames)))
        info_layout.addRow("Duration:", QLabel(f"{total_seconds:.1f} seconds"))
        layout.addWidget(info_group)
        
        # Frame limit group
        limit_group = QGroupBox("Detection Range")
        limit_layout = QFormLayout(limit_group)
        
        # Percentage slider
        self.percent_spin = QSpinBox()
        self.percent_spin.setRange(1, 100)
        self.percent_spin.setValue(100)
        self.percent_spin.setSuffix("%")
        self.percent_spin.valueChanged.connect(self._on_percent_changed)
        limit_layout.addRow("Process:", self.percent_spin)
        
        # Calculated info labels
        self.frames_label = QLabel(str(total_frames))
        self.seconds_label = QLabel(f"{total_seconds:.1f} s")
        self.estimate_label = QLabel("")
        self.estimate_label.setStyleSheet("color: #888; font-style: italic;")
        limit_layout.addRow("Frames:", self.frames_label)
        limit_layout.addRow("Video Duration:", self.seconds_label)
        limit_layout.addRow("Est. Processing:", self.estimate_label)
        
        # Note about ETA
        note_label = QLabel("(Actual ETA shown during processing)")
        note_label.setStyleSheet("color: #666; font-size: 10px;")
        limit_layout.addRow("", note_label)
        
        layout.addWidget(limit_group)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self._on_percent_changed(100)
    
    def _on_percent_changed(self, percent: int):
        """Update frame count, duration, and estimate labels based on percentage."""
        frames = int(self.total_frames * percent / 100)
        frames = max(1, frames)  # At least 1 frame
        video_seconds = frames / self.fps if self.fps > 0 else 0
        
        # Estimated processing time
        process_seconds = frames / self.ESTIMATED_FPS
        
        self.frames_label.setText(str(frames))
        self.seconds_label.setText(f"{video_seconds:.1f} s")
        self.estimate_label.setText(self._format_estimate(process_seconds))
    
    def _format_estimate(self, seconds: float) -> str:
        """Format processing time estimate in human-readable form."""
        if seconds < 60:
            return f"~{seconds:.0f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"~{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"~{hours:.1f} hours"
    
    def get_frame_limit(self) -> int:
        """Returns the number of frames to process (0 = all)."""
        percent = self.percent_spin.value()
        if percent >= 100:
            return 0  # 0 means all frames
        return max(1, int(self.total_frames * percent / 100))


class ExportThread(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, exporter, output_path, visible_classes):
        super().__init__()
        self.exporter = exporter
        self.output_path = output_path
        self.visible_classes = visible_classes

    def run(self):
        try:
            self.exporter.export(
                self.output_path, 
                self.visible_classes, 
                lambda current, total: self.progress.emit(current, total)
            )
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self, config: dict, frame_loader=None, results_cache=None, config_path: str = None):
        super().__init__()
        self.config = config
        self.config_path = config_path
        self.frame_loader = frame_loader
        self.results_cache = results_cache
        self.playback_controller = None
        self.calibration_controller = None
        self.drum_calibration_controller = None
        self.roi_controller = None
        self.setWindowTitle("MillPresenter")
        self.resize(1280, 720)

        # Status Bar for instructions
        self.setStatusBar(QStatusBar())

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout(central_widget)
        
        # Video Widget
        self.video_widget = VideoWidget(config)
        self.video_widget.clicked.connect(self._on_video_clicked)
        layout.addWidget(self.video_widget, stretch=1)
        
        # Controls
        controls_layout = QHBoxLayout()
        layout.addLayout(controls_layout)
        
        self.play_button = QPushButton("Play")
        self.play_button.setCheckable(True)
        self.play_button.toggled.connect(self.toggle_playback)
        controls_layout.addWidget(self.play_button)

        # Playback speed selector
        self.speed_combo = QComboBox()
        for label, speed in [("0.15x", 0.15), ("0.25x", 0.25), ("0.5x", 0.5), ("1.0x", 1.0)]:
            self.speed_combo.addItem(label, speed)
        self.speed_combo.setCurrentIndex(3)  # default 1.0x
        self.speed_combo.currentIndexChanged.connect(self._on_speed_changed)
        controls_layout.addWidget(self.speed_combo)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self._on_slider_moved)
        controls_layout.addWidget(self.slider)
        
        # Time Label
        self.time_label = QLabel("00:00 / 00:00")
        controls_layout.addWidget(self.time_label)
        
        # Manual Calibration Button (2-point)
        self.calibrate_btn = QPushButton("Manual")
        self.calibrate_btn.setCheckable(True)
        self.calibrate_btn.toggled.connect(self.toggle_calibration)
        controls_layout.addWidget(self.calibrate_btn)
        
        # Drum Calibration Button (auto-detect)
        self.drum_btn = QPushButton("Drum")
        self.drum_btn.setCheckable(True)
        self.drum_btn.toggled.connect(self.toggle_drum_calibration)
        controls_layout.addWidget(self.drum_btn)

        # ROI Button
        self.roi_btn = QPushButton("ROI Mask")
        self.roi_btn.setCheckable(True)
        self.roi_btn.toggled.connect(self.toggle_roi)
        controls_layout.addWidget(self.roi_btn)

        # Run Detection Button
        self.detect_btn = QPushButton("Run Detection")
        self.detect_btn.clicked.connect(self.run_detection)
        controls_layout.addWidget(self.detect_btn)

        # Export Button
        self.export_btn = QPushButton("Export MP4")
        self.export_btn.clicked.connect(self.export_video)
        controls_layout.addWidget(self.export_btn)

        # Toggles - Size filter buttons with colored backgrounds
        self.toggles = {}
        colors = self.config.get('overlay', {}).get('colors', {})
        
        for size in [4, 6, 8, 10]:
            btn = QPushButton(f"{size}mm")
            btn.setCheckable(True)
            btn.setChecked(True)
            
            # Apply color from config - colored background with contrasting text
            color_hex = colors.get(size, "#808080")
            # Use white text for dark colors, black for light (yellow)
            text_color = "#000000" if size == 10 else "#FFFFFF"  # Yellow needs black text
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color_hex};
                    color: {text_color};
                    font-weight: bold;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                }}
                QPushButton:checked {{
                    background-color: {color_hex};
                }}
                QPushButton:!checked {{
                    background-color: #555555;
                    color: #AAAAAA;
                }}
            """)
            
            btn.toggled.connect(lambda checked, s=size: self.toggle_class(s, checked))
            controls_layout.addWidget(btn)
            self.toggles[size] = btn

        # Initialize Controllers
        self.calibration_controller = CalibrationController(self.video_widget, self.config)
        self.drum_calibration_controller = DrumCalibrationController(self.video_widget, self.config)
        self.drum_calibration_controller.on_calibration_confirmed = self._on_drum_calibration_confirmed
        self.roi_controller = ROIController(self.video_widget)
        
        # Connect ROI signals
        self.video_widget.mouse_pressed.connect(self.roi_controller.handle_mouse_press)
        self.video_widget.mouse_moved.connect(self.roi_controller.handle_mouse_move)
        self.video_widget.mouse_released.connect(self.roi_controller.handle_mouse_release)
        
        # Connect Drum Calibration mouse signals
        self.video_widget.mouse_pressed.connect(self._on_drum_mouse_press)
        self.video_widget.mouse_moved.connect(self._on_drum_mouse_move)
        self.video_widget.mouse_released.connect(self._on_drum_mouse_release)

        if frame_loader and results_cache:
            self.attach_playback_sources(frame_loader, results_cache)

    def _on_drum_mouse_press(self, x, y, is_right_click):
        """Forward mouse press to drum calibration controller."""
        if self.drum_calibration_controller and self.drum_calibration_controller.is_active:
            from PyQt6.QtCore import QPoint
            self.drum_calibration_controller.handle_mouse_press(QPoint(int(x), int(y)))

    def _on_drum_mouse_move(self, x, y):
        """Forward mouse move to drum calibration controller."""
        if self.drum_calibration_controller and self.drum_calibration_controller.is_active:
            from PyQt6.QtCore import QPoint
            self.drum_calibration_controller.handle_mouse_move(QPoint(int(x), int(y)))

    def _on_drum_mouse_release(self, x, y):
        """Forward mouse release to drum calibration controller."""
        if self.drum_calibration_controller and self.drum_calibration_controller.is_active:
            from PyQt6.QtCore import QPoint
            self.drum_calibration_controller.handle_mouse_release(QPoint(int(x), int(y)))

    def export_video(self):
        if not self.frame_loader or not self.results_cache:
            QMessageBox.warning(self, "Error", "No video loaded.")
            return

        # Pause playback
        if self.playback_controller and self.playback_controller.is_playing:
            self.play_button.setChecked(False)

        # Get output path
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Export Video", "export.mp4", "MP4 Video (*.mp4)"
        )
        
        if not output_path:
            return

        # Create Exporter
        exporter = VideoExporter(self.config, self.frame_loader, self.results_cache)
        
        # Create Progress Dialog
        self.progress_dialog = QProgressDialog("Exporting video...", "Cancel", 0, self.frame_loader.total_frames, self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        
        # Create Thread
        self.export_thread = ExportThread(exporter, output_path, self.video_widget.visible_classes)
        self.export_thread.progress.connect(self.progress_dialog.setValue)
        self.export_thread.finished.connect(self._on_export_finished)
        self.export_thread.error.connect(self._on_export_error)
        
        # Handle Cancel
        self.progress_dialog.canceled.connect(self.export_thread.terminate) # Rough cancel
        
        self.export_thread.start()

    def toggle_calibration(self, active: bool):
        if active:
            # Disable other modes
            if hasattr(self, 'roi_btn') and self.roi_btn.isChecked():
                self.roi_btn.setChecked(False)
            if hasattr(self, 'drum_btn') and self.drum_btn.isChecked():
                self.drum_btn.setChecked(False)  # Cancel drum mode

            # Pause playback
            if self.playback_controller and self.playback_controller.is_playing:
                self.play_button.setChecked(False) # This triggers toggle_playback(False)
            
            self.calibration_controller.start()
            self.statusBar().showMessage("Manual Calibration: Click the START point of the known object.")
        else:
            self.calibration_controller.cancel()
            self.statusBar().clearMessage()

    def toggle_drum_calibration(self, active: bool):
        if active:
            # Disable other modes
            if hasattr(self, 'roi_btn') and self.roi_btn.isChecked():
                self.roi_btn.setChecked(False)
            if hasattr(self, 'calibrate_btn') and self.calibrate_btn.isChecked():
                self.calibrate_btn.setChecked(False)  # Cancel manual mode

            # Pause playback
            if self.playback_controller and self.playback_controller.is_playing:
                self.play_button.setChecked(False)
            
            # Auto-detect drum and show overlay for confirmation
            success = self.drum_calibration_controller.auto_detect_and_show()
            if success:
                self.statusBar().showMessage("Drum Calibration: Drag to adjust, then press Enter to confirm or Escape to cancel.")
            else:
                self.statusBar().showMessage("Failed to detect drum. Try manual calibration.")
                self.drum_btn.setChecked(False)
        else:
            self.drum_calibration_controller.cancel()
            self.statusBar().clearMessage()

    def _on_drum_calibration_confirmed(self, px_per_mm, center_point, radius):
        """Called when user confirms drum calibration."""
        self.save_config()
        self.drum_btn.setChecked(False)
        msg = f"Drum Calibration saved: {px_per_mm:.2f} px/mm"
        self.statusBar().showMessage(msg, 5000)

    def _on_video_clicked(self, x, y):
        if self.calibration_controller and self.calibration_controller.is_active:
            self.calibration_controller.handle_click(x, y)
            
            num_points = len(self.calibration_controller.points)
            
            if num_points == 1:
                self.statusBar().showMessage("Calibration Mode: Click the END point.")
            elif num_points == 2:
                self.statusBar().showMessage("Enter the physical distance in the dialog...")
                # Ask for distance
                distance, ok = QInputDialog.getDouble(
                    self, "Calibration", "Enter distance in mm:", 
                    value=10.0, min=0.1, max=10000.0, decimals=2
                )
                if ok:
                    self.calibration_controller.set_known_distance(distance)
                    self.calibration_controller.apply()
                    self.save_config()
                    self.calibrate_btn.setChecked(False)
                    msg = f"Calibration saved: {self.config['calibration']['px_per_mm']:.2f} px/mm"
                    self.statusBar().showMessage(msg, 5000) # Show for 5 seconds
                else:
                    # User cancelled dialog, reset points but keep mode active? 
                    # Or cancel mode? Let's reset points.
                    self.calibration_controller.points = []
                    self.video_widget.set_calibration_points([])
                    self.statusBar().showMessage("Calibration canceled. Click start point again.")

    def toggle_class(self, size: int, visible: bool):
        if visible:
            self.video_widget.visible_classes.add(size)
        else:
            self.video_widget.visible_classes.discard(size)
        self.video_widget.update()

    def attach_playback_sources(self, frame_loader, results_cache):
        self.playback_controller = PlaybackController(
            frame_loader,
            results_cache,
            self.video_widget,
            parent=self,
        )
        
        # Configure slider range
        total_frames = getattr(frame_loader, "total_frames", 0)
        if total_frames > 0:
            self.slider.setRange(0, total_frames - 1)
            
        # Connect controller updates to slider
        self.playback_controller.frame_changed.connect(self._on_frame_changed)

    def _on_slider_moved(self, value):
        if self.playback_controller:
            self.playback_controller.seek(value)

    def _on_frame_changed(self, frame_index):
        # Update slider without triggering signals to avoid feedback loop
        self.slider.blockSignals(True)
        self.slider.setValue(frame_index)
        self.slider.blockSignals(False)
        
        # Update Time Label
        if self.frame_loader and self.frame_loader.fps > 0:
            current_seconds = frame_index / self.frame_loader.fps
            total_seconds = self.frame_loader.total_frames / self.frame_loader.fps
            
            current_str = self._format_time(current_seconds)
            total_str = self._format_time(total_seconds)
            self.time_label.setText(f"{current_str} / {total_str}")

    def _format_time(self, seconds: float) -> str:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"

    def toggle_playback(self, playing: bool):
        if not self.playback_controller:
            # Reset button state if controller missing
            self.play_button.setChecked(False)
            return

        if playing:
            self.play_button.setText("Pause")
            self.playback_controller.play()
        else:
            self.play_button.setText("Play")
            self.playback_controller.pause()

    def _on_speed_changed(self, index: int) -> None:
        speed = self.speed_combo.currentData()
        if speed is None:
            return
        if self.playback_controller and hasattr(self.playback_controller, "set_playback_speed"):
            self.playback_controller.set_playback_speed(float(speed))

    def save_config(self):
        if not self.config_path:
            return
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(self.config, f, default_flow_style=False)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save config: {e}")

    def toggle_roi(self, active: bool):
        if active:
            # Disable other modes
            if self.calibrate_btn.isChecked():
                self.calibrate_btn.setChecked(False)
            
            # Pause playback
            if self.playback_controller and self.playback_controller.is_playing:
                self.play_button.setChecked(False)
                
            self.roi_controller.start()
            self.statusBar().showMessage("ROI Mode: Left Click to Mask (Ignore), Right Click to Erase (Valid).")
        else:
            self.roi_controller.cancel()
            # Save mask?
            # We should probably save when exiting mode or have a save button.
            # For now, let's save on exit mode.
            # Where to save? Same dir as video? Or config dir?
            # The instructions say "roi_mask.png".
            # Let's assume current working dir or detections dir.
            # Let's use detections dir from config.
            detections_dir = self.config.get('paths', {}).get('detections_dir', '.')
            mask_path = f"{detections_dir}/roi_mask.png"
            self.roi_controller.save(mask_path)
            self.statusBar().showMessage(f"ROI Mask saved to {mask_path}", 5000)

    def keyPressEvent(self, event):
        """Handle keyboard input for drum calibration confirmation."""
        if self.drum_calibration_controller and self.drum_calibration_controller.is_active:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                # Prompt for diameter before confirming
                current_diameter = self.drum_calibration_controller.drum_diameter_mm
                diameter, ok = QInputDialog.getDouble(
                    self, "Drum Calibration", 
                    "Enter drum diameter in mm:",
                    value=current_diameter, min=10.0, max=1000.0, decimals=1
                )
                if ok:
                    # Update the diameter and confirm
                    self.drum_calibration_controller.drum_diameter_mm = diameter
                    # Also update config for persistence
                    if 'calibration' not in self.config:
                        self.config['calibration'] = {}
                    self.config['calibration']['drum_diameter_mm'] = diameter
                    self.drum_calibration_controller.confirm()
                # If cancelled, stay in calibration mode
            elif event.key() == Qt.Key.Key_Escape:
                self.drum_btn.setChecked(False)  # This triggers toggle_drum_calibration(False)
        else:
            super().keyPressEvent(event)

    # ─────────────────────────────────────────────────────────────────────────
    # Detection Methods
    # ─────────────────────────────────────────────────────────────────────────

    def run_detection(self):
        """Launch background detection with progress dialog."""
        if not self.frame_loader:
            QMessageBox.warning(self, "Error", "No video loaded.")
            return
        
        # Pause playback
        if self.playback_controller and self.playback_controller.is_playing:
            self.play_button.setChecked(False)
        
        # Show detection configuration dialog
        dialog = DetectionDialog(
            self.frame_loader.total_frames,
            self.frame_loader.fps,
            parent=self
        )
        
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        frame_limit = dialog.get_frame_limit()
        
        # Determine output path based on video name
        video_path = self.frame_loader.file_path
        output_path = get_detection_path(video_path)
        
        # Get ROI mask - prefer saved file, fallback to controller's current mask
        roi_mask = None
        
        # Check for saved ROI mask file
        detections_dir = self.config.get('paths', {}).get('detections_dir', '.')
        roi_mask_path = f"{detections_dir}/roi_mask.png"
        
        if os.path.exists(roi_mask_path):
            # Load saved mask (already in correct format: white=valid, black=ignore)
            roi_mask = cv2.imread(roi_mask_path, cv2.IMREAD_GRAYSCALE)
            if roi_mask is not None:
                print(f"Loaded ROI mask from {roi_mask_path}")
        elif self.roi_controller and self.roi_controller.center_point is not None:
            # Generate mask from ROI controller's circle definition
            if self.frame_loader and hasattr(self.frame_loader, 'width') and hasattr(self.frame_loader, 'height'):
                width = self.frame_loader.width
                height = self.frame_loader.height
            elif self.video_widget.current_image:
                width = self.video_widget.current_image.width()
                height = self.video_widget.current_image.height()
            else:
                width, height = 1920, 1080  # Fallback
            
            # Create binary mask from circle
            roi_mask = np.zeros((height, width), dtype=np.uint8)
            center = (int(self.roi_controller.center_point.x()), int(self.roi_controller.center_point.y()))
            radius = int(self.roi_controller.current_radius)
            cv2.circle(roi_mask, center, radius, 255, -1)  # White filled circle
            print(f"Generated ROI mask from circle: center={center}, radius={radius}")
        
        # Debug: Report ROI mask status
        if roi_mask is not None:
            white_pixels = np.sum(roi_mask > 0)
            total_pixels = roi_mask.shape[0] * roi_mask.shape[1]
            print(f"ROI mask loaded: shape={roi_mask.shape}, valid_area={white_pixels}/{total_pixels} ({100*white_pixels/total_pixels:.1f}%)")
        else:
            print("No ROI mask - processing entire frame")
        
        # Calculate total frames for progress
        total_frames = frame_limit if frame_limit > 0 else self.frame_loader.total_frames
        
        # Track start time for ETA calculation
        import time
        self._detect_start_time = time.time()
        self._detect_total_frames = total_frames
        
        # Create progress dialog
        self.detect_progress = QProgressDialog(
            "Running detection... (calculating ETA)", "Cancel", 0, total_frames, self
        )
        self.detect_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.detect_progress.setMinimumDuration(0)
        
        # Create and start detection thread
        self.detect_thread = DetectionThread(
            video_path=video_path,
            config=self.config,
            output_path=output_path,
            roi_mask=roi_mask,
            limit=frame_limit if frame_limit > 0 else None,
            parent=self
        )
        
        self.detect_thread.progress.connect(self._on_detection_progress)
        self.detect_thread.finished.connect(self._on_detection_finished)
        self.detect_thread.error.connect(self._on_detection_error)
        self.detect_progress.canceled.connect(self.detect_thread.cancel)
        
        self.detect_thread.start()

    def _on_detection_progress(self, current: int, total: int):
        """Update progress dialog with ETA."""
        import time
        self.detect_progress.setValue(current)
        
        if current > 0:
            elapsed = time.time() - self._detect_start_time
            fps = current / elapsed
            remaining_frames = total - current
            eta_seconds = remaining_frames / fps if fps > 0 else 0
            
            # Format ETA
            if eta_seconds < 60:
                eta_str = f"{eta_seconds:.0f}s"
            elif eta_seconds < 3600:
                eta_str = f"{eta_seconds/60:.1f}min"
            else:
                eta_str = f"{eta_seconds/3600:.1f}h"
            
            self.detect_progress.setLabelText(
                f"Processing frame {current}/{total} ({fps:.1f} fps)\n"
                f"ETA: {eta_str}"
            )

    def _on_detection_finished(self, detections_path: str):
        """Handle successful detection completion."""
        self.detect_progress.close()
        
        # Reload cache with new detections
        self.results_cache = ResultsCache(detections_path)
        
        # Re-attach playback sources to use new cache
        if self.frame_loader:
            self.attach_playback_sources(self.frame_loader, self.results_cache)
        
        QMessageBox.information(
            self, "Detection Complete",
            f"Detections saved to:\n{detections_path}\n\n"
            f"Loaded {len(self.results_cache._memory_cache)} frames."
        )
        self.statusBar().showMessage("Detection complete. Overlays ready.", 5000)

    def _on_detection_error(self, error_msg: str):
        """Handle detection failure."""
        self.detect_progress.close()
        QMessageBox.critical(
            self, "Detection Failed",
            f"Error during detection:\n{error_msg}"
        )
        self.statusBar().showMessage("Detection failed.", 5000)

    # ─────────────────────────────────────────────────────────────────────────
    # Export Handlers
    # ─────────────────────────────────────────────────────────────────────────

    def _on_export_finished(self):
        """Handle successful export completion."""
        self.progress_dialog.close()
        QMessageBox.information(
            self, "Export Complete",
            "Video exported successfully!"
        )
        self.statusBar().showMessage("Export complete.", 5000)

    def _on_export_error(self, error_msg: str):
        """Handle export failure."""
        self.progress_dialog.close()
        QMessageBox.critical(
            self, "Export Failed",
            f"Error during export:\n{error_msg}"
        )
        self.statusBar().showMessage("Export failed.", 5000)
