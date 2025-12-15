from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QSlider, QInputDialog, QMessageBox, QStatusBar, QFileDialog, QProgressDialog, QLabel
import yaml
from mill_presenter.ui.widgets import VideoWidget
from mill_presenter.ui.playback_controller import PlaybackController
from mill_presenter.ui.calibration_controller import CalibrationController
from mill_presenter.ui.drum_calibration_controller import DrumCalibrationController
from mill_presenter.ui.roi_controller import ROIController
from mill_presenter.core.exporter import VideoExporter

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
