"""
MillPresenter Main Window

The central QMainWindow containing all UI panels in a 5-region layout:
- [A] Top Bar: Status and file info
- [B] Video Viewport: Central video display
- [C] Right Panel: Tabbed controls
- [D] Bottom Bar: Timeline and transport
- [E] Left Panel: Statistics

Layout Pattern:
┌───────────────────────────────────────────────────────────────┐
│                        [A] TOP BAR                            │
├────────────┬──────────────────────────────────┬───────────────┤
│            │                                  │               │
│ [E] LEFT   │        [B] VIDEO VIEWPORT        │  [C] RIGHT    │
│   PANEL    │                                  │    PANEL      │
│            │                                  │               │
├────────────┴──────────────────────────────────┴───────────────┤
│                       [D] BOTTOM BAR                          │
└───────────────────────────────────────────────────────────────┘

HCI Principles Applied:
- Fitts's Law: Large central viewport, controls at edges
- Visibility: Status always visible in top bar
- Consistency: Standard media player layout patterns
"""

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QMenu, QFileDialog, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QAction, QKeySequence, QShortcut

from ui.theme import COLORS, DIMENSIONS, get_application_stylesheet
from ui.state import AppState, AppStateManager, VideoInfo, CacheInfo
from ui.widgets import TopBar, BottomBar, LeftPanel, RightPanel, VideoViewport
from ui.video_controller import VideoController, DetectionCache
from ui.detection_worker import DetectionController, DetectionParams


class MainWindow(QMainWindow):
    """
    Main application window for MillPresenter.
    
    Manages the 5-panel layout and coordinates between components
    via the centralized AppStateManager.
    """
    
    def __init__(self):
        super().__init__()
        
        # State management
        self.state_manager = AppStateManager(self)
        
        # Video controller
        self.video_controller = VideoController(self)
        self.detection_cache = DetectionCache()
        
        # Detection controller for preview and batch processing
        self.detection_controller = DetectionController(self)
        
        # Drum geometry (set when video loaded or from calibration)
        self._drum_center = None
        self._drum_radius = 0
        self._last_frame_index = -1  # Track frame changes to clear preview
        
        # Setup
        self._setup_window()
        self._setup_menu_bar()
        self._setup_layout()
        self._setup_shortcuts()
        self._connect_signals()
        
        # Initial state sync
        self._sync_state()
    
    def _setup_window(self):
        """Configure main window properties."""
        self.setWindowTitle("MillPresenter")
        self.setMinimumSize(DIMENSIONS.MIN_WIDTH, DIMENSIONS.MIN_HEIGHT)
        self.resize(DIMENSIONS.DEFAULT_WIDTH, DIMENSIONS.DEFAULT_HEIGHT)
        
        # Apply dark theme stylesheet
        self.setStyleSheet(get_application_stylesheet())
    
    def _setup_menu_bar(self):
        """Create the menu bar."""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        
        self.open_action = QAction("&Open Video...", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.setToolTip("Open a video file (Ctrl+O)")
        self.open_action.triggered.connect(self._on_open_video)
        file_menu.addAction(self.open_action)
        
        self.load_cache_action = QAction("&Load Cache...", self)
        self.load_cache_action.setToolTip("Load detection cache for current video")
        self.load_cache_action.triggered.connect(self._on_load_cache)
        file_menu.addAction(self.load_cache_action)
        
        file_menu.addSeparator()
        
        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.triggered.connect(self.close)
        file_menu.addAction(self.exit_action)
        
        # View menu
        view_menu = menu_bar.addMenu("&View")
        
        self.toggle_left_panel_action = QAction("Toggle &Stats Panel", self)
        self.toggle_left_panel_action.setShortcut("Ctrl+H")
        self.toggle_left_panel_action.setCheckable(True)
        self.toggle_left_panel_action.setChecked(True)
        self.toggle_left_panel_action.triggered.connect(self._on_toggle_left_panel)
        view_menu.addAction(self.toggle_left_panel_action)
        
        self.fullscreen_action = QAction("&Full Screen", self)
        self.fullscreen_action.setShortcut(QKeySequence.StandardKey.FullScreen)
        self.fullscreen_action.setCheckable(True)
        self.fullscreen_action.triggered.connect(self._on_toggle_fullscreen)
        view_menu.addAction(self.fullscreen_action)
        
        view_menu.addSeparator()
        
        self.reset_view_action = QAction("&Reset Viewport", self)
        self.reset_view_action.triggered.connect(self._on_reset_viewport)
        view_menu.addAction(self.reset_view_action)
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        
        self.help_action = QAction("&Help", self)
        self.help_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        self.help_action.triggered.connect(self._on_show_help)
        help_menu.addAction(self.help_action)
        
        help_menu.addSeparator()
        
        self.about_action = QAction("&About", self)
        self.about_action.triggered.connect(self._on_show_about)
        help_menu.addAction(self.about_action)
    
    def _setup_layout(self):
        """Create the 5-panel layout with resizable side panels."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main vertical layout
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # [A] Top bar
        self.top_bar = TopBar(self.state_manager)
        main_layout.addWidget(self.top_bar)
        
        # Middle section: use QSplitter for resizable panels
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(4)  # Visible resize handle
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {COLORS.BORDER};
            }}
            QSplitter::handle:hover {{
                background: {COLORS.ACCENT};
            }}
        """)
        
        # [E] Left panel (resizable)
        self.left_panel = LeftPanel(self.state_manager)
        self.left_panel.setMinimumWidth(120)
        self.left_panel.setMaximumWidth(400)
        self.splitter.addWidget(self.left_panel)
        
        # [B] Video viewport (stretches)
        self.viewport = VideoViewport()
        self.splitter.addWidget(self.viewport)
        
        # [C] Right panel (resizable)
        self.right_panel = RightPanel(self.state_manager)
        self.right_panel.setMinimumWidth(150)
        self.right_panel.setMaximumWidth(450)
        self.splitter.addWidget(self.right_panel)
        
        # Set initial sizes (left, center, right)
        self.splitter.setSizes([DIMENSIONS.LEFT_PANEL_WIDTH, 800, DIMENSIONS.RIGHT_PANEL_WIDTH])
        
        # Make center panel stretch priority
        self.splitter.setStretchFactor(0, 0)  # Left: don't stretch
        self.splitter.setStretchFactor(1, 1)  # Center: stretch
        self.splitter.setStretchFactor(2, 0)  # Right: don't stretch
        
        main_layout.addWidget(self.splitter, stretch=1)
        
        # [D] Bottom bar
        self.bottom_bar = BottomBar(self.state_manager)
        main_layout.addWidget(self.bottom_bar)
    
    def _setup_shortcuts(self):
        """Configure keyboard shortcuts."""
        # Playback shortcuts (only work when viewport has focus)
        # Note: F11 is not included here as it's already registered via fullscreen_action.setShortcut()
        shortcuts = [
            ("Space", self._on_play_pause),
            ("Left", self._on_step_backward),
            ("Right", self._on_step_forward),
            ("Shift+Left", self._on_jump_backward),
            ("Shift+Right", self._on_jump_forward),
            ("Home", self._on_go_to_start),
            ("End", self._on_go_to_end),
            ("L", self._on_toggle_loop),
        ]
        
        for key, callback in shortcuts:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)
    
    def _connect_signals(self):
        """Connect widget signals to handlers."""
        # State manager
        self.state_manager.state_changed.connect(self._on_state_changed)
        self.state_manager.error_occurred.connect(self._on_error)
        
        # Video controller
        self.video_controller.frame_ready.connect(self._on_frame_ready)
        self.video_controller.playback_finished.connect(self._on_playback_finished)
        self.video_controller.error_occurred.connect(self._on_error)
        
        # Detection controller
        self.detection_controller.preview_ready.connect(self._on_preview_ready)
        self.detection_controller.batch_progress.connect(self._on_batch_progress)
        self.detection_controller.batch_finished.connect(self._on_batch_finished)
        self.detection_controller.error.connect(self._on_error)
        
        # Bottom bar transport controls
        self.bottom_bar.play_toggled.connect(self._on_play_toggled)
        self.bottom_bar.frame_changed.connect(self._on_frame_changed)
        self.bottom_bar.speed_changed.connect(self._on_speed_changed)
        self.bottom_bar.step_forward.connect(self._on_step_forward)
        self.bottom_bar.step_backward.connect(self._on_step_backward)
        self.bottom_bar.jump_forward.connect(self._on_jump_forward)
        self.bottom_bar.jump_backward.connect(self._on_jump_backward)
        self.bottom_bar.go_to_start.connect(self._on_go_to_start)
        self.bottom_bar.go_to_end.connect(self._on_go_to_end)
        self.bottom_bar.loop_toggled.connect(self._on_loop_toggled)
        self.bottom_bar.fullscreen_toggled.connect(self._on_toggle_fullscreen)
        
        # Right panel
        self.right_panel.overlay_settings_changed.connect(self._on_overlay_settings_changed)
        self.right_panel.run_detection.connect(self._on_run_detection)
        self.right_panel.cancel_detection.connect(self._on_cancel_detection)
        self.right_panel.preview_requested.connect(self._on_preview_requested)
        self.right_panel.show_roi_toggled.connect(self._on_show_roi)
        self.right_panel.two_point_mode_changed.connect(self._on_two_point_mode)
        self.right_panel.roi_adjusted.connect(self._on_roi_adjusted)
        self.right_panel.calibration_changed.connect(self._on_calibration_changed)
        self.right_panel.recalculate_requested.connect(self._on_recalculate_requested)
        self.right_panel.export_csv.connect(self._on_export_csv)
        self.right_panel.export_json.connect(self._on_export_json)
        self.right_panel.save_frame.connect(self._on_save_frame)
        
        # Viewport
        self.viewport.detection_hovered.connect(self._on_detection_hovered)
        self.viewport.two_point_measured.connect(self._on_two_point_measured)
        self.viewport.roi_drag_finished.connect(self._on_roi_drag_finished)
    
    def _sync_state(self):
        """Synchronize UI with current state."""
        state = self.state_manager.state
        
        # Update menu states
        self.load_cache_action.setEnabled(
            state in (AppState.VIDEO_LOADED, AppState.CACHE_READY)
        )
    
    # =========================================================================
    # Menu Actions
    # =========================================================================
    
    @Slot()
    def _on_open_video(self):
        """Open video file dialog."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv);;All Files (*)"
        )
        
        if file_path:
            self._load_video(file_path)
    
    @Slot()
    def _on_load_cache(self):
        """Load detection cache file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Detection Cache",
            "cache/detections",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            self._load_cache(file_path)
    
    @Slot(bool)
    def _on_toggle_left_panel(self, visible: bool):
        """Show/hide left stats panel."""
        self.left_panel.setVisible(visible)
    
    @Slot()
    def _on_toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_action.setChecked(False)
        else:
            self.showFullScreen()
            self.fullscreen_action.setChecked(True)
    
    @Slot()
    def _on_reset_viewport(self):
        """Reset viewport zoom/pan."""
        self.viewport.reset_view()
    
    @Slot()
    def _on_show_help(self):
        """Show help dialog."""
        help_text = """
        <h2>MillPresenter Help</h2>
        
        <h3>Keyboard Shortcuts</h3>
        <table>
        <tr><td><b>Space</b></td><td>Play/Pause</td></tr>
        <tr><td><b>←/→</b></td><td>Step ±1 frame</td></tr>
        <tr><td><b>Shift+←/→</b></td><td>Step ±10 frames</td></tr>
        <tr><td><b>Home/End</b></td><td>First/Last frame</td></tr>
        <tr><td><b>L</b></td><td>Toggle loop</td></tr>
        <tr><td><b>F11</b></td><td>Toggle fullscreen</td></tr>
        <tr><td><b>Ctrl+H</b></td><td>Toggle stats panel</td></tr>
        <tr><td><b>Ctrl+O</b></td><td>Open video</td></tr>
        </table>
        
        <h3>Viewport Controls</h3>
        <ul>
        <li><b>Mouse wheel:</b> Zoom in/out</li>
        <li><b>Drag (when zoomed):</b> Pan view</li>
        <li><b>Double-click:</b> Reset view</li>
        </ul>
        """
        
        QMessageBox.information(self, "Help", help_text)
    
    @Slot()
    def _on_show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About MillPresenter",
            "<h2>MillPresenter</h2>"
            "<p>Version 1.0.0</p>"
            "<p>A desktop application for visualizing grinding mill "
            "video analysis results.</p>"
            "<p>Detects and classifies metallic beads in rotating drum videos.</p>"
        )
    
    # =========================================================================
    # State Handlers
    # =========================================================================
    
    @Slot(AppState, AppState)
    def _on_state_changed(self, old_state: AppState, new_state: AppState):
        """Handle application state changes."""
        self._sync_state()
    
    @Slot(str)
    def _on_error(self, message: str):
        """Display error message."""
        QMessageBox.critical(self, "Error", message)
    
    # =========================================================================
    # Playback Handlers
    # =========================================================================
    
    @Slot(bool)
    def _on_play_toggled(self, playing: bool):
        """Handle play/pause toggle."""
        self.state_manager.playback.is_playing = playing
        self.state_manager.update_playback()
        
        if playing:
            self.video_controller.play()
        else:
            self.video_controller.pause()
    
    @Slot()
    def _on_play_pause(self):
        """Toggle play/pause from shortcut."""
        if self.state_manager.can_play():
            playing = self.video_controller.toggle_play()
            self.bottom_bar.set_playing(playing)
    
    @Slot(int)
    def _on_frame_changed(self, frame: int):
        """Handle timeline seek."""
        self.state_manager.playback.current_frame = frame
        self.state_manager.update_playback()
        self.video_controller.seek(frame)
    
    @Slot(float)
    def _on_speed_changed(self, speed: float):
        """Handle playback speed change."""
        self.state_manager.playback.playback_speed = speed
        self.state_manager.update_playback()
        self.video_controller.set_speed(speed)
    
    @Slot()
    def _on_step_forward(self):
        """Step one frame forward."""
        if self.state_manager.can_play():
            self.video_controller.step_forward(1)
    
    @Slot()
    def _on_step_backward(self):
        """Step one frame backward."""
        if self.state_manager.can_play():
            self.video_controller.step_backward(1)
    
    @Slot()
    def _on_jump_forward(self):
        """Jump 10 frames forward."""
        if self.state_manager.can_play():
            self.video_controller.step_forward(10)
    
    @Slot()
    def _on_jump_backward(self):
        """Jump 10 frames backward."""
        if self.state_manager.can_play():
            self.video_controller.step_backward(10)
    
    @Slot()
    def _on_go_to_start(self):
        """Go to first frame."""
        if self.state_manager.can_play():
            self.video_controller.go_to_start()
    
    @Slot()
    def _on_go_to_end(self):
        """Go to last frame."""
        if self.state_manager.can_play():
            self.video_controller.go_to_end()
    
    @Slot(bool)
    def _on_loop_toggled(self, looping: bool):
        """Handle loop toggle."""
        self.state_manager.playback.is_looping = looping
        self.state_manager.update_playback()
        self.video_controller.set_looping(looping)
    
    @Slot()
    def _on_toggle_loop(self):
        """Toggle loop from shortcut."""
        looping = not self.state_manager.playback.is_looping
        self._on_loop_toggled(looping)
    
    @Slot(object, int)
    def _on_frame_ready(self, frame, frame_index: int):
        """Handle new frame from video controller."""
        import numpy as np
        if isinstance(frame, np.ndarray):
            # Clear preview detections if we're on a different frame
            if frame_index != self._last_frame_index:
                self.viewport.clear_preview_detections()
                self._last_frame_index = frame_index
            
            # Update viewport with new frame
            self.viewport.set_frame(frame)
            
            # Update bottom bar position
            self.bottom_bar.set_current_frame(frame_index)
            
            # Update state
            self.state_manager.playback.current_frame = frame_index
            
            # If we have detection cache, load detections for this frame
            if self.detection_cache.is_loaded:
                detections = self.detection_cache.get_detections(frame_index)
                self.viewport.set_detections(detections)
                
                # Update left panel stats
                stats = self.detection_cache.get_stats(frame_index)
                by_class = {
                    "4mm": stats.get("4mm", 0),
                    "6mm": stats.get("6mm", 0),
                    "8mm": stats.get("8mm", 0),
                    "10mm": stats.get("10mm", 0),
                }
                conf_bins = self.detection_cache.get_confidence_bins(frame_index)
                self.left_panel.update_stats(stats.get("total", 0), by_class, conf_bins)
    
    @Slot()
    def _on_playback_finished(self):
        """Handle playback reaching end."""
        self.bottom_bar.set_playing(False)
    
    # =========================================================================
    # Overlay Handlers
    # =========================================================================
    
    @Slot(object)
    def _on_overlay_settings_changed(self, settings):
        """Handle overlay settings change."""
        self.state_manager.overlay = settings
        self.state_manager.update_overlay()
        
        # Apply to viewport
        self.viewport.set_overlay_visibility(settings.show_overlays)
        self.viewport.set_overlay_opacity(settings.opacity)
        self.viewport.set_min_confidence(settings.min_confidence)
        self.viewport.set_visible_classes(set(settings.get_visible_classes()))
        self.viewport.set_label_options(
            settings.show_size_labels, 
            settings.show_confidence_labels
        )
    
    @Slot(bool)
    def _on_show_roi(self, show: bool):
        """Toggle ROI visualization."""
        self.viewport.show_roi(show)
    
    @Slot(bool)
    def _on_two_point_mode(self, enabled: bool):
        """Handle two-point measurement mode toggle."""
        self.viewport.set_two_point_mode(enabled)
    
    @Slot(float)
    def _on_two_point_measured(self, pixel_distance: float):
        """Handle two-point measurement completion."""
        self.right_panel.calibration_tab.set_pixel_distance(pixel_distance)
    
    @Slot(int, int, int)
    def _on_roi_adjusted(self, cx: int, cy: int, radius: int):
        """Handle ROI adjustment from calibration tab."""
        self._drum_center = (cx, cy)
        self._drum_radius = radius
        self.viewport.set_drum_roi((cx, cy), radius, self.viewport._show_roi)
    
    @Slot(int, int, int)
    def _on_roi_drag_finished(self, cx: int, cy: int, radius: int):
        """Handle ROI adjustment from viewport drag."""
        self._drum_center = (cx, cy)
        self._drum_radius = radius
        self.right_panel.calibration_tab.set_roi(cx, cy, radius)
    
    @Slot(float)
    def _on_calibration_changed(self, px_per_mm: float):
        """Handle calibration value change."""
        self._px_per_mm = px_per_mm
        self.right_panel.calibration_tab.set_calibration(px_per_mm)
        self.right_panel.process_tab.log(f"Calibration set to {px_per_mm:.2f} px/mm")
    
    @Slot()
    def _on_recalculate_requested(self):
        """Handle recalculate classifications request."""
        if not hasattr(self, '_px_per_mm') or self._px_per_mm <= 0:
            self.right_panel.process_tab.log("No valid calibration set")
            return
        
        # Reclassify all cached detections
        if self.detection_cache.is_loaded:
            count = self.detection_cache.reclassify_all(self._px_per_mm)
            self.right_panel.process_tab.log(f"Reclassified {count} detections")
            # Refresh current frame display by seeking to the current frame
            current_frame = self.state_manager.playback.current_frame
            self.video_controller.seek(current_frame)
        else:
            self.right_panel.process_tab.log("No detections to reclassify")
    
    @Slot(dict)
    def _on_detection_hovered(self, detection: dict):
        """Handle detection hover (for tooltips)."""
        if detection:
            # Could show tooltip or update status
            pass
    
    # =========================================================================
    # Processing Handlers
    # =========================================================================
    
    @Slot()
    def _on_run_detection(self):
        """Start batch detection processing."""
        if not self.state_manager.can_process():
            return
        
        video_info = self.state_manager.video
        if not video_info:
            return
        
        # Get current parameters from ProcessTab
        params = self._get_detection_params()
        
        # Get frame count selection
        frame_count = self.right_panel.process_tab.get_frame_count()
        total_frames = video_info.total_frames
        
        # Calculate frame step or limit
        if frame_count == -1:
            # All frames
            num_frames = total_frames
            frame_step = 1
        elif frame_count == 1:
            # Single frame - use preview instead
            self._on_preview_requested(self.right_panel.process_tab.get_params())
            return
        else:
            # Limited frames - calculate step to distribute evenly
            num_frames = min(frame_count, total_frames)
            frame_step = max(1, total_frames // num_frames)
        
        self.state_manager.set_state(AppState.PROCESSING)
        self.right_panel.process_tab.log(f"Starting detection on {num_frames} frames (step={frame_step})...")
        self.right_panel.process_tab.progress.show()
        self.right_panel.process_tab.cancel_btn.show()
        
        # Start batch detection
        self.detection_controller.start_batch(
            video_info.path,
            params,
            self._drum_center,
            self._drum_radius,
            frame_step=frame_step
        )
    
    @Slot()
    def _on_cancel_detection(self):
        """Cancel detection processing."""
        self.detection_controller.cancel_batch()
        self.state_manager.set_state(AppState.VIDEO_LOADED)
        self.right_panel.process_tab.log("Detection cancelled.")
        self.right_panel.process_tab.progress.hide()
        self.right_panel.process_tab.cancel_btn.hide()
    
    @Slot(dict)
    def _on_preview_requested(self, params_dict: dict):
        """Handle preview request from ProcessTab."""
        # Get current frame from video controller
        frame = self.video_controller.get_current_frame()
        if frame is None:
            self.right_panel.process_tab.log("No frame available for preview")
            return
        
        # Convert dict to DetectionParams
        params = DetectionParams.from_dict(params_dict)
        
        # Request preview (debounced)
        self.detection_controller.request_preview(
            frame,
            params,
            self._drum_center,
            self._drum_radius
        )
        self.right_panel.process_tab.log("Running preview detection...")
    
    @Slot(list)
    def _on_preview_ready(self, detections: list):
        """Handle preview detection results."""
        count = len(detections)
        self.right_panel.process_tab.log(f"Preview: {count} detections found")
        
        # Show preview detections on viewport
        self.viewport.set_preview_detections(detections)
    
    @Slot(int, str)
    def _on_batch_progress(self, percent: int, message: str):
        """Handle batch progress updates."""
        self.right_panel.process_tab.progress.setValue(percent)
        self.right_panel.process_tab.set_status(message)
    
    @Slot(dict)
    def _on_batch_finished(self, cache_data: dict):
        """Handle batch detection completion."""
        self.right_panel.process_tab.log("Batch detection complete!")
        self.right_panel.process_tab.progress.hide()
        self.right_panel.process_tab.cancel_btn.hide()
        
        # Load cache data
        self.detection_cache.load_from_dict(cache_data)
        
        # Update state
        self.state_manager.set_state(AppState.CACHE_READY)
        self.right_panel.process_tab.clear_unsaved_changes()
    
    def _get_detection_params(self) -> DetectionParams:
        """Get current detection parameters from ProcessTab sliders."""
        tab = self.right_panel.process_tab
        return DetectionParams(
            blur_kernel=int(tab.blur_slider.get_value()),
            canny_low=int(tab.canny_low_slider.get_value()),
            canny_high=int(tab.canny_high_slider.get_value()),
            hough_dp=tab.hough_dp_slider.get_value(),
            hough_param2=int(tab.hough_param2_slider.get_value()),
            hough_min_dist=int(tab.min_dist_slider.get_value()),
        )
    
    # =========================================================================
    # Export Handlers
    # =========================================================================
    
    @Slot()
    def _on_export_csv(self):
        """Export detections to CSV."""
        if not self.state_manager.can_export():
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            # TODO: Export logic
            QMessageBox.information(self, "Export", f"Exported to {file_path}")
    
    @Slot()
    def _on_export_json(self):
        """Export detections to JSON."""
        if not self.state_manager.can_export():
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export JSON", "", "JSON Files (*.json)"
        )
        
        if file_path:
            # TODO: Export logic
            QMessageBox.information(self, "Export", f"Exported to {file_path}")
    
    @Slot()
    def _on_save_frame(self):
        """Save current frame as PNG."""
        if not self.state_manager.can_export():
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Frame", "", "PNG Images (*.png)"
        )
        
        if file_path:
            # TODO: Save frame logic
            QMessageBox.information(self, "Save", f"Saved to {file_path}")
    
    # =========================================================================
    # Video/Cache Loading
    # =========================================================================
    
    def _load_video(self, file_path: str):
        """Load a video file."""
        try:
            # Use video controller to open and display video
            if not self.video_controller.open(file_path):
                raise ValueError(f"Cannot open video: {file_path}")
            
            # Update state with video info
            video_info = VideoInfo(
                path=file_path,
                name=Path(file_path).stem,
                width=self.video_controller.width,
                height=self.video_controller.height,
                fps=self.video_controller.fps,
                total_frames=self.video_controller.total_frames,
                duration_seconds=self.video_controller.duration_seconds
            )
            
            self.state_manager.set_video(video_info)
            self.state_manager.set_state(AppState.VIDEO_LOADED)
            
            # Set default drum geometry (frame center, radius = 40% of min dimension)
            # This allows preview to work before calibration
            cx = self.video_controller.width // 2
            cy = self.video_controller.height // 2
            radius = min(self.video_controller.width, self.video_controller.height) // 2 - 20
            self._drum_center = (cx, cy)
            self._drum_radius = radius
            self.viewport.set_drum_roi((cx, cy), radius, show=False)
            
            # Initialize calibration tab with ROI values
            self.right_panel.calibration_tab.set_roi(cx, cy, radius)
            
            # Update bottom bar
            self.bottom_bar.set_video_info(
                self.video_controller.total_frames,
                self.video_controller.fps
            )
            
            # Check for existing cache
            self._try_auto_load_cache(file_path)
            
        except Exception as e:
            self.state_manager.set_error(str(e))
    
    def _load_cache(self, file_path: str):
        """Load a detection cache file."""
        try:
            if not self.detection_cache.load(file_path):
                raise ValueError(f"Failed to load cache: {file_path}")
            
            cache_info = CacheInfo(
                path=file_path,
                total_frames=self.detection_cache.total_frames,
                px_per_mm=self.detection_cache.px_per_mm,
                drum_center=self.detection_cache.drum_center,
                drum_radius=self.detection_cache.drum_radius,
                is_loaded=True
            )
            
            self.state_manager.set_cache(cache_info)
            self.state_manager.set_state(AppState.CACHE_READY)
            
            # Update drum geometry from cache
            self._drum_center = cache_info.drum_center
            self._drum_radius = cache_info.drum_radius
            
            # Set drum ROI on viewport
            self.viewport.set_drum_roi(
                cache_info.drum_center,
                cache_info.drum_radius,
                show=False
            )
            
            # Load detections for current frame
            current_frame = self.video_controller.current_frame
            detections = self.detection_cache.get_detections(current_frame)
            self.viewport.set_detections(detections)
            
            self.right_panel.process_tab.log(f"Loaded cache: {file_path}")
            
        except Exception as e:
            self.state_manager.set_error(f"Failed to load cache: {e}")
    
    def _try_auto_load_cache(self, video_path: str):
        """Try to automatically load matching cache file."""
        video_name = Path(video_path).stem
        cache_path = Path("cache/detections") / f"{video_name}_detections.json"
        
        if cache_path.exists():
            self._load_cache(str(cache_path))
