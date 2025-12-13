"""
Right Panel Widget

Tabbed control panel for overlay settings, processing, calibration, and export.

Layout:
┌────────────────┐
│Overlay│Proc│...│  (Tabs)
├────────────────┤
│ Show Overlays  │
│ ☑ Master       │
├────────────────┤
│ Opacity: 100%  │
│ ━━━━━━━━━━━━━━ │
├────────────────┤
│ Confidence     │
│ ━━━●━━━━━━━━━━ │
│ Min: 0.50      │
├────────────────┤
│ Class Toggles  │
│ ☑ ● 4mm        │
│ ☑ ● 6mm        │
│ ☑ ● 8mm        │
│ ☑ ● 10mm       │
├────────────────┤
│ Visual Options │
│ ☐ Size Labels  │
│ ☐ Conf Labels  │
└────────────────┘

HCI Principles Applied:
- Direct Manipulation: Sliders provide immediate visual feedback
- Consistency (Nielsen #4): Color swatches match overlay colors exactly
- Recognition (Nielsen #6): Checkboxes with colored indicators
"""

from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QCheckBox, QSlider, QPushButton, QSpinBox,
    QDoubleSpinBox, QProgressBar, QTextEdit, QRadioButton,
    QButtonGroup, QGroupBox, QSizePolicy, QScrollArea, QComboBox
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont

from ui.theme import COLORS, DIMENSIONS, TYPOGRAPHY, CLASS_COLORS
from ui.state import AppState, AppStateManager, OverlaySettings


class ClassToggle(QWidget):
    """Checkbox with colored dot for a size class."""
    
    toggled = Signal(str, bool)  # class_name, is_checked
    
    def __init__(self, class_name: str, parent=None):
        super().__init__(parent)
        self.class_name = class_name
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(6)
        
        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.stateChanged.connect(self._on_state_changed)
        layout.addWidget(self.checkbox)
        
        # Color dot
        color = CLASS_COLORS.get_hex(self.class_name)
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {color}; font-size: 14px;")
        self.dot.setFixedWidth(18)
        layout.addWidget(self.dot)
        
        # Label
        self.label = QLabel(self.class_name)
        layout.addWidget(self.label)
        
        layout.addStretch(1)
    
    def _on_state_changed(self, state):
        self.toggled.emit(self.class_name, state == Qt.CheckState.Checked.value)
    
    def set_checked(self, checked: bool):
        self.checkbox.setChecked(checked)
    
    def is_checked(self) -> bool:
        return self.checkbox.isChecked()


class LabeledSlider(QWidget):
    """Slider with label, value display, and optional info button."""
    
    value_changed = Signal(float)
    
    def __init__(self, label: str, min_val: float, max_val: float, 
                 decimals: int = 0, suffix: str = "", 
                 tooltip: str = "", info_text: str = "", parent=None):
        super().__init__(parent)
        
        self._min = min_val
        self._max = max_val
        self._decimals = decimals
        self._suffix = suffix
        self._scale = 10 ** decimals
        self._label_text = label
        self._info_text = info_text
        
        self._setup_ui(label, tooltip, info_text)
    
    def _setup_ui(self, label: str, tooltip: str, info_text: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)
        
        # Header row
        header = QHBoxLayout()
        
        self.label = QLabel(label)
        self.label.setProperty("secondary", True)
        header.addWidget(self.label)
        
        # Info button (ⓘ) - only show if info_text provided
        if info_text:
            from PySide6.QtWidgets import QToolButton, QMessageBox
            self.info_btn = QToolButton()
            self.info_btn.setText("ⓘ")
            self.info_btn.setStyleSheet(f"""
                QToolButton {{
                    border: none;
                    color: {COLORS.TEXT_SECONDARY};
                    font-size: 12pt;
                    padding: 0 4px;
                }}
                QToolButton:hover {{
                    color: {COLORS.ACCENT};
                }}
            """)
            self.info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.info_btn.setToolTip("Click for detailed explanation")
            self.info_btn.clicked.connect(self._show_info_popup)
            header.addWidget(self.info_btn)
        
        header.addStretch(1)
        
        self.value_label = QLabel()
        header.addWidget(self.value_label)
        
        layout.addLayout(header)
        
        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(int(self._min * self._scale))
        self.slider.setMaximum(int(self._max * self._scale))
        self.slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.slider)
        
        # Set tooltip on entire widget
        if tooltip:
            self.setToolTip(tooltip)
        
        # Set initial value display
        self._update_value_label(self._min)
    
    def _show_info_popup(self):
        """Show detailed info popup when ⓘ is clicked."""
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle(f"Parameter: {self._label_text}")
        msg.setText(self._info_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
    
    def _on_slider_changed(self, value: int):
        float_val = value / self._scale
        self._update_value_label(float_val)
        self.value_changed.emit(float_val)
    
    def _update_value_label(self, value: float):
        if self._decimals == 0:
            text = f"{int(value)}{self._suffix}"
        else:
            text = f"{value:.{self._decimals}f}{self._suffix}"
        self.value_label.setText(text)
    
    def set_value(self, value: float):
        self.slider.setValue(int(value * self._scale))
    
    def get_value(self) -> float:
        return self.slider.value() / self._scale
    
    def value(self) -> float:
        return self.get_value()


class OverlayTab(QWidget):
    """Overlay visualization controls."""
    
    settings_changed = Signal(OverlaySettings)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = OverlaySettings()
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # Master toggle
        self.master_toggle = QCheckBox("Show Overlays")
        self.master_toggle.setChecked(True)
        self.master_toggle.stateChanged.connect(self._on_master_changed)
        layout.addWidget(self.master_toggle)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)
        
        # Opacity slider
        self.opacity_slider = LabeledSlider("Opacity", 0, 100, 0, "%")
        self.opacity_slider.set_value(100)
        self.opacity_slider.value_changed.connect(self._on_opacity_changed)
        layout.addWidget(self.opacity_slider)
        
        # Confidence threshold
        self.conf_slider = LabeledSlider("Min Confidence", 0.0, 1.0, 2)
        self.conf_slider.set_value(0.0)
        self.conf_slider.value_changed.connect(self._on_confidence_changed)
        layout.addWidget(self.conf_slider)
        
        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep2)
        
        # Class toggles section
        class_label = QLabel("Size Classes")
        class_label.setProperty("secondary", True)
        layout.addWidget(class_label)
        
        self.class_toggles = {}
        for cls in CLASS_COLORS.all_classes():
            toggle = ClassToggle(cls)
            toggle.toggled.connect(self._on_class_toggled)
            self.class_toggles[cls] = toggle
            layout.addWidget(toggle)
        
        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep3)
        
        # Visual options section
        options_label = QLabel("Visual Options")
        options_label.setProperty("secondary", True)
        layout.addWidget(options_label)
        
        self.show_size_labels = QCheckBox("Show Size Labels")
        self.show_size_labels.stateChanged.connect(self._on_option_changed)
        layout.addWidget(self.show_size_labels)
        
        self.show_conf_labels = QCheckBox("Show Confidence Labels")
        self.show_conf_labels.stateChanged.connect(self._on_option_changed)
        layout.addWidget(self.show_conf_labels)
        
        # Spacer
        layout.addStretch(1)
    
    def _emit_settings(self):
        """Emit current settings."""
        self.settings_changed.emit(self._settings)
    
    def _on_master_changed(self, state):
        self._settings.show_overlays = state == Qt.CheckState.Checked.value
        self._emit_settings()
    
    def _on_opacity_changed(self, value):
        self._settings.opacity = value / 100.0
        self._emit_settings()
    
    def _on_confidence_changed(self, value):
        self._settings.min_confidence = value
        self._emit_settings()
    
    def _on_class_toggled(self, class_name: str, checked: bool):
        if class_name == "4mm":
            self._settings.show_4mm = checked
        elif class_name == "6mm":
            self._settings.show_6mm = checked
        elif class_name == "8mm":
            self._settings.show_8mm = checked
        elif class_name == "10mm":
            self._settings.show_10mm = checked
        self._emit_settings()
    
    def _on_option_changed(self, state):
        self._settings.show_size_labels = self.show_size_labels.isChecked()
        self._settings.show_confidence_labels = self.show_conf_labels.isChecked()
        self._emit_settings()
    
    def get_settings(self) -> OverlaySettings:
        return self._settings
    
    def set_settings(self, settings: OverlaySettings):
        """Apply settings to controls."""
        self._settings = settings
        
        # Block signals during update
        self.master_toggle.blockSignals(True)
        self.opacity_slider.slider.blockSignals(True)
        self.conf_slider.slider.blockSignals(True)
        
        self.master_toggle.setChecked(settings.show_overlays)
        self.opacity_slider.set_value(settings.opacity * 100)
        self.conf_slider.set_value(settings.min_confidence)
        
        for cls, toggle in self.class_toggles.items():
            toggle.checkbox.blockSignals(True)
            if cls == "4mm":
                toggle.set_checked(settings.show_4mm)
            elif cls == "6mm":
                toggle.set_checked(settings.show_6mm)
            elif cls == "8mm":
                toggle.set_checked(settings.show_8mm)
            elif cls == "10mm":
                toggle.set_checked(settings.show_10mm)
            toggle.checkbox.blockSignals(False)
        
        self.show_size_labels.blockSignals(True)
        self.show_conf_labels.blockSignals(True)
        self.show_size_labels.setChecked(settings.show_size_labels)
        self.show_conf_labels.setChecked(settings.show_confidence_labels)
        self.show_size_labels.blockSignals(False)
        self.show_conf_labels.blockSignals(False)
        
        self.master_toggle.blockSignals(False)
        self.opacity_slider.slider.blockSignals(False)
        self.conf_slider.slider.blockSignals(False)


class ProcessTab(QWidget):
    """
    Detection processing controls with Real-Time/Offline mode switch.
    
    Real-Time Mode: Runs detection on current frame only for preview
    Offline Mode: Queues changes, applies to all frames on "Apply"
    """
    
    # Default parameters (proven values from testing)
    DEFAULT_PARAMS = {
        "blur_kernel": 7,
        "canny_low": 50,
        "canny_high": 150,
        "hough_dp": 1.0,
        "hough_param2": 25,
        "hough_min_dist": 15,
    }
    
    run_detection = Signal()
    cancel_detection = Signal()
    preview_requested = Signal(dict)  # Detection params for preview
    params_changed = Signal(dict)  # Current params
    mode_changed = Signal(str)  # "realtime" or "offline"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_processing = False
        self._is_realtime = False
        self._has_unsaved_changes = False
        self._saved_params = {}
        self._setup_ui()
    
    def _setup_ui(self):
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        
        # ─────────────────────────────────────────────────────────
        # MODE SELECTOR
        # ─────────────────────────────────────────────────────────
        mode_group = QGroupBox("Tuning Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        self.mode_btn_group = QButtonGroup(self)
        
        self.offline_radio = QRadioButton("Offline (Batch)")
        self.offline_radio.setChecked(True)
        self.offline_radio.setToolTip(
            "Queue parameter changes. Click 'Apply to All' to process entire video."
        )
        self.mode_btn_group.addButton(self.offline_radio)
        mode_layout.addWidget(self.offline_radio)
        
        self.realtime_radio = QRadioButton("Real-Time Preview")
        self.realtime_radio.setToolTip(
            "Preview detection on current frame instantly. "
            "Useful for fine-tuning before batch processing."
        )
        self.mode_btn_group.addButton(self.realtime_radio)
        mode_layout.addWidget(self.realtime_radio)
        
        self.offline_radio.toggled.connect(self._on_mode_changed)
        
        layout.addWidget(mode_group)
        
        # ─────────────────────────────────────────────────────────
        # DETECTION PARAMETERS
        # ─────────────────────────────────────────────────────────
        params_group = QGroupBox("Detection Parameters")
        params_layout = QVBoxLayout(params_group)
        params_layout.setSpacing(8)
        
        # Blur kernel
        self.blur_slider = LabeledSlider(
            "Blur Kernel", 1, 15, decimals=0,
            tooltip="Smoothing amount. Higher = less noise, may miss small beads.",
            info_text=(
                "Blur Kernel Size\n\n"
                "Controls the Gaussian blur applied before edge detection.\n\n"
                "• Lower values (1-3): Preserves fine details but may introduce noise\n"
                "• Medium values (5-7): Good balance for most videos\n"
                "• Higher values (9-15): Reduces noise but may merge adjacent beads\n\n"
                "Tip: Start with 7 and adjust based on video quality."
            )
        )
        self.blur_slider.set_value(7)  # Proven default from testing
        self.blur_slider.value_changed.connect(self._on_param_changed)
        params_layout.addWidget(self.blur_slider)
        
        # Canny thresholds
        self.canny_low_slider = LabeledSlider(
            "Canny Low", 10, 150, decimals=0,
            tooltip="Lower edge threshold. Decrease to detect more edges.",
            info_text=(
                "Canny Edge Detection - Low Threshold\n\n"
                "Sets the minimum gradient strength to consider as an edge.\n\n"
                "• Lower values (10-30): Detects more edges, including weak ones\n"
                "• Medium values (40-80): Standard sensitivity\n"
                "• Higher values (90-150): Only strong edges detected\n\n"
                "Should be lower than Canny High. Typical ratio is 1:2 or 1:3."
            )
        )
        self.canny_low_slider.set_value(50)
        self.canny_low_slider.value_changed.connect(self._on_param_changed)
        params_layout.addWidget(self.canny_low_slider)
        
        self.canny_high_slider = LabeledSlider(
            "Canny High", 50, 300, decimals=0,
            tooltip="Upper edge threshold. Increase to filter weak edges.",
            info_text=(
                "Canny Edge Detection - High Threshold\n\n"
                "Sets the maximum gradient strength for edge linking.\n\n"
                "• Lower values (50-100): More permissive, detects faint edges\n"
                "• Medium values (100-200): Balanced detection\n"
                "• Higher values (200-300): Only very strong edges survive\n\n"
                "Should be higher than Canny Low. Increase if seeing too many false edges."
            )
        )
        self.canny_high_slider.set_value(150)
        self.canny_high_slider.value_changed.connect(self._on_param_changed)
        params_layout.addWidget(self.canny_high_slider)
        
        # Hough parameters
        self.hough_dp_slider = LabeledSlider(
            "Hough dp", 1.0, 2.5, decimals=1,
            tooltip="Accumulator resolution. Higher = faster but less precise.",
            info_text=(
                "Hough Transform - Accumulator Resolution (dp)\n\n"
                "Controls the resolution of the accumulator array.\n\n"
                "• dp = 1.0: Same resolution as input image (most accurate)\n"
                "• dp = 1.5: Half resolution (faster, slightly less accurate)\n"
                "• dp = 2.0+: Lower resolution (fastest, may miss circles)\n\n"
                "Start with 1.0 for accuracy, increase for speed."
            )
        )
        self.hough_dp_slider.set_value(1.0)  # Most accurate setting
        self.hough_dp_slider.value_changed.connect(self._on_param_changed)
        params_layout.addWidget(self.hough_dp_slider)
        
        self.hough_param2_slider = LabeledSlider(
            "Sensitivity", 10, 60, decimals=0,
            tooltip="Lower = more detections (more false positives)",
            info_text=(
                "Hough Transform - Sensitivity (param2)\n\n"
                "Accumulator threshold for circle detection.\n\n"
                "• Lower values (10-20): Very sensitive, detects more circles\n"
                "  → May include false positives (glare, drum features)\n"
                "• Medium values (25-40): Balanced detection\n"
                "• Higher values (45-60): Strict, only high-confidence circles\n"
                "  → May miss some valid beads\n\n"
                "This is the most important tuning parameter!"
            )
        )
        self.hough_param2_slider.set_value(25)  # Balanced sensitivity
        self.hough_param2_slider.value_changed.connect(self._on_param_changed)
        params_layout.addWidget(self.hough_param2_slider)
        
        # Min distance
        self.min_dist_slider = LabeledSlider(
            "Min Distance", 5, 50, decimals=0, suffix="px",
            tooltip="Minimum spacing between detected circles.",
            info_text=(
                "Minimum Distance Between Circles\n\n"
                "Minimum pixel distance between detected circle centers.\n\n"
                "• Lower values (5-15): Allows tightly packed detections\n"
                "  → Risk of detecting same bead multiple times\n"
                "• Medium values (20-30): Good for typical bead density\n"
                "• Higher values (35-50): Forces more spacing\n"
                "  → May miss adjacent beads in dense areas\n\n"
                "Set based on smallest expected bead size in pixels."
            )
        )
        self.min_dist_slider.set_value(15)  # Allow tighter bead packing
        self.min_dist_slider.value_changed.connect(self._on_param_changed)
        params_layout.addWidget(self.min_dist_slider)
        
        layout.addWidget(params_group)
        
        # ─────────────────────────────────────────────────────────
        # FRAME COUNT SELECTOR (for limited detection runs)
        # ─────────────────────────────────────────────────────────
        frames_group = QGroupBox("Detection Range")
        frames_layout = QVBoxLayout(frames_group)
        
        frames_label = QLabel("Number of frames to process:")
        frames_layout.addWidget(frames_label)
        
        self.frame_count_combo = QComboBox()
        self.frame_count_combo.addItem("Current Frame Only", 1)
        self.frame_count_combo.addItem("10 Frames", 10)
        self.frame_count_combo.addItem("30 Frames", 30)
        self.frame_count_combo.addItem("100 Frames", 100)
        self.frame_count_combo.addItem("All Frames", -1)  # -1 means all
        self.frame_count_combo.setCurrentIndex(4)  # Default to "All Frames"
        self.frame_count_combo.setToolTip(
            "Select how many frames to process.\n"
            "Use smaller values for quick testing,\n"
            "'All Frames' for final processing."
        )
        frames_layout.addWidget(self.frame_count_combo)
        
        layout.addWidget(frames_group)
        
        # ─────────────────────────────────────────────────────────
        # RESET TO DEFAULTS BUTTON
        # ─────────────────────────────────────────────────────────
        self.reset_btn = QPushButton("↺ Reset to Defaults")
        self.reset_btn.setToolTip("Reset all parameters to proven default values")
        self.reset_btn.clicked.connect(self._on_reset_clicked)
        layout.addWidget(self.reset_btn)
        
        # ─────────────────────────────────────────────────────────
        # UNSAVED CHANGES INDICATOR
        # ─────────────────────────────────────────────────────────
        self.unsaved_label = QLabel("⚠ Unsaved changes")
        self.unsaved_label.setStyleSheet(f"color: {COLORS.STATUS_PROCESSING}; font-weight: bold;")
        self.unsaved_label.hide()
        layout.addWidget(self.unsaved_label)
        
        # ─────────────────────────────────────────────────────────
        # ACTION BUTTONS
        # ─────────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("Preview Frame")
        self.preview_btn.setToolTip("Run detection on current frame only")
        self.preview_btn.clicked.connect(self._on_preview_clicked)
        btn_layout.addWidget(self.preview_btn)
        
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setProperty("accent", True)
        self.apply_btn.setToolTip("Run detection on selected frames (see 'Detection Range')")
        self.apply_btn.clicked.connect(self._on_apply_clicked)
        btn_layout.addWidget(self.apply_btn)
        
        layout.addLayout(btn_layout)
        
        # Cancel button (shown during processing)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_detection.emit)
        self.cancel_btn.hide()
        layout.addWidget(self.cancel_btn)
        
        # ─────────────────────────────────────────────────────────
        # PROGRESS
        # ─────────────────────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.hide()
        layout.addWidget(self.progress)
        
        self.status_label = QLabel("Ready")
        self.status_label.setProperty("secondary", True)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # ─────────────────────────────────────────────────────────
        # LOG OUTPUT
        # ─────────────────────────────────────────────────────────
        log_label = QLabel("Log")
        log_label.setProperty("secondary", True)
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS.BG_INPUT};
                font-family: {TYPOGRAPHY.FONT_FAMILY_MONO};
                font-size: {TYPOGRAPHY.SIZE_SMALL}pt;
            }}
        """)
        layout.addWidget(self.log_text)
        
        layout.addStretch(1)
        
        scroll.setWidget(content)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def _on_mode_changed(self, checked: bool):
        """Handle mode radio button change."""
        self._is_realtime = self.realtime_radio.isChecked()
        mode = "realtime" if self._is_realtime else "offline"
        self.mode_changed.emit(mode)
        
        # In realtime mode, trigger preview on param changes
        if self._is_realtime:
            self.status_label.setText("Real-time: changes preview instantly")
            self._trigger_preview()
        else:
            self.status_label.setText("Offline: click 'Apply to All' when ready")
    
    def _on_param_changed(self, value):
        """Handle any parameter slider change."""
        params = self.get_params()
        self.params_changed.emit(params)
        
        # Check for unsaved changes
        if self._saved_params and params != self._saved_params:
            self._has_unsaved_changes = True
            self.unsaved_label.show()
        
        # In realtime mode, trigger preview
        if self._is_realtime:
            self._trigger_preview()
    
    def _trigger_preview(self):
        """Request a preview detection."""
        self.preview_requested.emit(self.get_params())
    
    def _on_preview_clicked(self):
        """Manual preview button click."""
        self._trigger_preview()
    
    def _on_apply_clicked(self):
        """Apply parameters to all frames."""
        self._saved_params = self.get_params()
        self._has_unsaved_changes = False
        self.unsaved_label.hide()
        self.run_detection.emit()
    
    def _on_reset_clicked(self):
        """Reset all parameters to proven defaults."""
        self.blur_slider.set_value(self.DEFAULT_PARAMS["blur_kernel"])
        self.canny_low_slider.set_value(self.DEFAULT_PARAMS["canny_low"])
        self.canny_high_slider.set_value(self.DEFAULT_PARAMS["canny_high"])
        self.hough_dp_slider.set_value(self.DEFAULT_PARAMS["hough_dp"])
        self.hough_param2_slider.set_value(self.DEFAULT_PARAMS["hough_param2"])
        self.min_dist_slider.set_value(self.DEFAULT_PARAMS["hough_min_dist"])
        self.log("Parameters reset to defaults")
    
    def get_params(self) -> dict:
        """Get current detection parameters."""
        # Ensure blur kernel is odd
        blur = int(self.blur_slider.get_value())
        if blur % 2 == 0:
            blur = max(1, blur - 1)
        
        return {
            "blur_kernel": blur,
            "canny_low": int(self.canny_low_slider.get_value()),
            "canny_high": int(self.canny_high_slider.get_value()),
            "hough_dp": self.hough_dp_slider.get_value(),
            "hough_param2": int(self.hough_param2_slider.get_value()),
            "hough_min_dist": int(self.min_dist_slider.get_value()),
        }
    
    def set_params(self, params: dict):
        """Set detection parameters from dict."""
        if "blur_kernel" in params:
            self.blur_slider.set_value(params["blur_kernel"])
        if "canny_low" in params:
            self.canny_low_slider.set_value(params["canny_low"])
        if "canny_high" in params:
            self.canny_high_slider.set_value(params["canny_high"])
        if "hough_dp" in params:
            self.hough_dp_slider.set_value(params["hough_dp"])
        if "hough_param2" in params:
            self.hough_param2_slider.set_value(params["hough_param2"])
        if "hough_min_dist" in params:
            self.min_dist_slider.set_value(params["hough_min_dist"])
        
        self._saved_params = params.copy()
        self._has_unsaved_changes = False
        self.unsaved_label.hide()
    
    def get_frame_count(self) -> int:
        """
        Get the selected number of frames to process.
        
        Returns:
            Number of frames, or -1 for "All Frames".
        """
        return self.frame_count_combo.currentData()
    
    def set_processing(self, is_processing: bool):
        """Update UI for processing state."""
        self._is_processing = is_processing
        
        if is_processing:
            self.preview_btn.hide()
            self.apply_btn.hide()
            self.cancel_btn.show()
            self.progress.show()
            self.status_label.setText("Processing...")
            # Disable param sliders during processing
            self._set_params_enabled(False)
        else:
            self.preview_btn.show()
            self.apply_btn.show()
            self.cancel_btn.hide()
            self.progress.hide()
            self._set_params_enabled(True)
        
        self.cancel_btn.style().unpolish(self.cancel_btn)
        self.cancel_btn.style().polish(self.cancel_btn)
    
    def _set_params_enabled(self, enabled: bool):
        """Enable/disable parameter sliders."""
        self.blur_slider.setEnabled(enabled)
        self.canny_low_slider.setEnabled(enabled)
        self.canny_high_slider.setEnabled(enabled)
        self.hough_dp_slider.setEnabled(enabled)
        self.hough_param2_slider.setEnabled(enabled)
        self.min_dist_slider.setEnabled(enabled)
        self.offline_radio.setEnabled(enabled)
        self.realtime_radio.setEnabled(enabled)
    
    def set_progress(self, percent: int, message: str = ""):
        """Update progress display."""
        self.progress.setValue(percent)
        if message:
            self.status_label.setText(message)
    
    def set_status(self, message: str):
        """Set status label text."""
        self.status_label.setText(message)
    
    def clear_unsaved_changes(self):
        """Clear the unsaved changes flag and hide indicator."""
        self._has_unsaved_changes = False
        self.unsaved_label.hide()
    
    def log(self, message: str):
        """Add message to log."""
        self.log_text.append(message)
    
    def clear_log(self):
        """Clear the log."""
        self.log_text.clear()
    
    def set_enabled(self, enabled: bool):
        """Enable/disable processing controls."""
        self.preview_btn.setEnabled(enabled)
        self.apply_btn.setEnabled(enabled)
        self._set_params_enabled(enabled)
    
    @property
    def is_realtime_mode(self) -> bool:
        return self._is_realtime


class CalibrationTab(QWidget):
    """Calibration controls with two-point measurement and ROI adjustment."""
    
    calibration_changed = Signal(float)  # new px_per_mm
    recalculate_requested = Signal()
    show_roi_toggled = Signal(bool)
    two_point_mode_changed = Signal(bool)  # True = start measuring, False = cancel
    roi_adjusted = Signal(int, int, int)  # center_x, center_y, radius
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._two_point_active = False
        self._setup_ui()
    
    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        
        # ─────────────────────────────────────────────────────────
        # CALIBRATION MODE
        # ─────────────────────────────────────────────────────────
        mode_group = QGroupBox("Calibration Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        self.mode_group = QButtonGroup(self)
        
        self.auto_radio = QRadioButton("Auto (from drum geometry)")
        self.auto_radio.setChecked(True)
        self.auto_radio.setToolTip("Automatically calculate px/mm from detected drum size")
        self.mode_group.addButton(self.auto_radio)
        mode_layout.addWidget(self.auto_radio)
        
        self.manual_radio = QRadioButton("Manual (enter value)")
        self.manual_radio.setToolTip("Manually enter the px/mm calibration value")
        self.mode_group.addButton(self.manual_radio)
        mode_layout.addWidget(self.manual_radio)
        
        self.twopoint_radio = QRadioButton("Two-Point Measurement")
        self.twopoint_radio.setToolTip("Click two points on frame and enter known distance")
        self.mode_group.addButton(self.twopoint_radio)
        mode_layout.addWidget(self.twopoint_radio)
        
        # Manual value input (shown for manual mode)
        manual_layout = QHBoxLayout()
        px_label = QLabel("px/mm:")
        manual_layout.addWidget(px_label)
        
        self.px_per_mm_input = QDoubleSpinBox()
        self.px_per_mm_input.setMinimum(0.1)
        self.px_per_mm_input.setMaximum(100.0)
        self.px_per_mm_input.setDecimals(2)
        self.px_per_mm_input.setValue(5.0)
        self.px_per_mm_input.setEnabled(False)
        manual_layout.addWidget(self.px_per_mm_input)
        mode_layout.addLayout(manual_layout)
        
        layout.addWidget(mode_group)
        
        # ─────────────────────────────────────────────────────────
        # TWO-POINT MEASUREMENT (only visible in two-point mode)
        # ─────────────────────────────────────────────────────────
        self.twopoint_group = QGroupBox("Two-Point Measurement")
        twopoint_layout = QVBoxLayout(self.twopoint_group)
        
        self.twopoint_instructions = QLabel(
            "1. Click 'Start Measurement'\n"
            "2. Click first point on frame\n"
            "3. Click second point on frame\n"
            "4. Enter known distance in mm"
        )
        self.twopoint_instructions.setWordWrap(True)
        self.twopoint_instructions.setProperty("secondary", True)
        twopoint_layout.addWidget(self.twopoint_instructions)
        
        self.start_measure_btn = QPushButton("Start Measurement")
        self.start_measure_btn.clicked.connect(self._on_start_measure)
        twopoint_layout.addWidget(self.start_measure_btn)
        
        # Distance input
        dist_layout = QHBoxLayout()
        dist_layout.addWidget(QLabel("Known distance (mm):"))
        self.distance_input = QDoubleSpinBox()
        self.distance_input.setMinimum(1.0)
        self.distance_input.setMaximum(500.0)
        self.distance_input.setValue(100.0)
        self.distance_input.setEnabled(False)
        dist_layout.addWidget(self.distance_input)
        twopoint_layout.addLayout(dist_layout)
        
        # Pixel distance display
        self.pixel_dist_label = QLabel("Pixel distance: -")
        self.pixel_dist_label.setProperty("secondary", True)
        twopoint_layout.addWidget(self.pixel_dist_label)
        
        self.apply_measure_btn = QPushButton("Apply Calibration")
        self.apply_measure_btn.setEnabled(False)
        self.apply_measure_btn.clicked.connect(self._on_apply_measurement)
        twopoint_layout.addWidget(self.apply_measure_btn)
        
        self.twopoint_group.hide()  # Hidden by default
        layout.addWidget(self.twopoint_group)
        
        # ─────────────────────────────────────────────────────────
        # DRUM ROI ADJUSTMENT
        # ─────────────────────────────────────────────────────────
        roi_group = QGroupBox("Drum ROI")
        roi_layout = QVBoxLayout(roi_group)
        
        self.show_roi = QCheckBox("Show Drum ROI (RED circle)")
        self.show_roi.stateChanged.connect(
            lambda s: self.show_roi_toggled.emit(s == Qt.CheckState.Checked.value)
        )
        roi_layout.addWidget(self.show_roi)
        
        roi_hint = QLabel(
            "Drag center to move, drag edge to resize.\n"
            "Use +/- buttons for fine adjustment."
        )
        roi_hint.setProperty("secondary", True)
        roi_hint.setWordWrap(True)
        roi_layout.addWidget(roi_hint)
        
        # ROI adjustment controls
        roi_adjust_layout = QHBoxLayout()
        
        self.roi_shrink_btn = QPushButton("-")
        self.roi_shrink_btn.setFixedWidth(30)
        self.roi_shrink_btn.setToolTip("Shrink ROI radius")
        self.roi_shrink_btn.clicked.connect(lambda: self._adjust_roi_radius(-5))
        roi_adjust_layout.addWidget(self.roi_shrink_btn)
        
        self.roi_radius_label = QLabel("Radius: -")
        roi_adjust_layout.addWidget(self.roi_radius_label, 1)
        
        self.roi_expand_btn = QPushButton("+")
        self.roi_expand_btn.setFixedWidth(30)
        self.roi_expand_btn.setToolTip("Expand ROI radius")
        self.roi_expand_btn.clicked.connect(lambda: self._adjust_roi_radius(5))
        roi_adjust_layout.addWidget(self.roi_expand_btn)
        
        roi_layout.addLayout(roi_adjust_layout)
        
        layout.addWidget(roi_group)
        
        # ─────────────────────────────────────────────────────────
        # ACTIONS
        # ─────────────────────────────────────────────────────────
        self.recalc_btn = QPushButton("Recalculate Classifications")
        self.recalc_btn.setToolTip("Re-classify bead sizes using current calibration")
        self.recalc_btn.clicked.connect(self.recalculate_requested.emit)
        layout.addWidget(self.recalc_btn)
        
        # Current calibration display
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)
        
        current_label = QLabel("Current Calibration")
        current_label.setProperty("secondary", True)
        layout.addWidget(current_label)
        
        self.current_value = QLabel("-")
        layout.addWidget(self.current_value)
        
        layout.addStretch(1)
        
        scroll.setWidget(content)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        
        # Connect mode changes
        self.manual_radio.toggled.connect(self._on_mode_changed)
        self.twopoint_radio.toggled.connect(self._on_twopoint_mode_changed)
        self.px_per_mm_input.valueChanged.connect(self._on_value_changed)
        
        # Store ROI values
        self._roi_center = (0, 0)
        self._roi_radius = 0
        self._pixel_distance = 0
    
    def _on_mode_changed(self, manual_checked: bool):
        """Handle manual mode toggle."""
        self.px_per_mm_input.setEnabled(manual_checked)
    
    def _on_twopoint_mode_changed(self, checked: bool):
        """Handle two-point mode toggle."""
        self.twopoint_group.setVisible(checked)
        if not checked:
            self._cancel_measurement()
    
    def _on_start_measure(self):
        """Start two-point measurement mode."""
        self._two_point_active = True
        self.start_measure_btn.setText("Cancel Measurement")
        self.start_measure_btn.clicked.disconnect()
        self.start_measure_btn.clicked.connect(self._cancel_measurement)
        self.two_point_mode_changed.emit(True)
        self.twopoint_instructions.setText("Click first point on the video frame...")
    
    def _cancel_measurement(self):
        """Cancel two-point measurement."""
        self._two_point_active = False
        self.start_measure_btn.setText("Start Measurement")
        self.start_measure_btn.clicked.disconnect()
        self.start_measure_btn.clicked.connect(self._on_start_measure)
        self.two_point_mode_changed.emit(False)
        self.distance_input.setEnabled(False)
        self.apply_measure_btn.setEnabled(False)
        self.pixel_dist_label.setText("Pixel distance: -")
        self.twopoint_instructions.setText(
            "1. Click 'Start Measurement'\n"
            "2. Click first point on frame\n"
            "3. Click second point on frame\n"
            "4. Enter known distance in mm"
        )
    
    def set_pixel_distance(self, pixel_dist: float):
        """Called when two points have been selected on viewport."""
        self._pixel_distance = pixel_dist
        self.pixel_dist_label.setText(f"Pixel distance: {pixel_dist:.1f} px")
        self.distance_input.setEnabled(True)
        self.apply_measure_btn.setEnabled(True)
        self.twopoint_instructions.setText("Enter the known distance and click Apply")
    
    def _on_apply_measurement(self):
        """Apply the two-point calibration."""
        if self._pixel_distance > 0:
            known_mm = self.distance_input.value()
            px_per_mm = self._pixel_distance / known_mm
            self.px_per_mm_input.setValue(px_per_mm)
            self.calibration_changed.emit(px_per_mm)
            self._cancel_measurement()
    
    def _on_value_changed(self, value: float):
        """Handle manual px/mm value change."""
        if self.manual_radio.isChecked():
            self.calibration_changed.emit(value)
    
    def _adjust_roi_radius(self, delta: int):
        """Adjust ROI radius by delta pixels."""
        new_radius = max(50, self._roi_radius + delta)
        self._roi_radius = new_radius
        self.roi_radius_label.setText(f"Radius: {new_radius} px")
        self.roi_adjusted.emit(self._roi_center[0], self._roi_center[1], new_radius)
    
    def set_roi(self, center_x: int, center_y: int, radius: int):
        """Set current ROI values."""
        self._roi_center = (center_x, center_y)
        self._roi_radius = radius
        self.roi_radius_label.setText(f"Radius: {radius} px")
    
    def set_calibration(self, px_per_mm: float):
        """Display current calibration value."""
        self.current_value.setText(f"{px_per_mm:.2f} px/mm")
        if self.auto_radio.isChecked():
            self.px_per_mm_input.setValue(px_per_mm)
    
    def get_px_per_mm(self) -> float:
        """Get current px/mm value."""
        return self.px_per_mm_input.value()
    
    def get_calibration(self) -> float:
        """Get current calibration value (alias for get_px_per_mm)."""
        return self.get_px_per_mm()
    
    def get_roi(self) -> tuple:
        """Get current ROI values (center_x, center_y, radius)."""
        return (self._roi_center[0], self._roi_center[1], self._roi_radius)
    
    def is_two_point_active(self) -> bool:
        """Check if two-point measurement is active."""
        return self._two_point_active


class ExportTab(QWidget):
    """Export controls."""
    
    export_csv = Signal()
    export_json = Signal()
    save_frame = Signal()
    export_video = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # Export section
        export_label = QLabel("Export Detections")
        export_label.setProperty("secondary", True)
        layout.addWidget(export_label)
        
        self.csv_btn = QPushButton("Export CSV")
        self.csv_btn.clicked.connect(self.export_csv.emit)
        layout.addWidget(self.csv_btn)
        
        self.json_btn = QPushButton("Export JSON")
        self.json_btn.clicked.connect(self.export_json.emit)
        layout.addWidget(self.json_btn)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)
        
        # Frame export
        frame_label = QLabel("Current Frame")
        frame_label.setProperty("secondary", True)
        layout.addWidget(frame_label)
        
        self.save_frame_btn = QPushButton("Save as PNG")
        self.save_frame_btn.clicked.connect(self.save_frame.emit)
        layout.addWidget(self.save_frame_btn)
        
        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep2)
        
        # Video export
        video_label = QLabel("Video with Overlays")
        video_label.setProperty("secondary", True)
        layout.addWidget(video_label)
        
        self.export_video_btn = QPushButton("Export Video...")
        self.export_video_btn.clicked.connect(self.export_video.emit)
        layout.addWidget(self.export_video_btn)
        
        # Spacer
        layout.addStretch(1)
    
    def set_enabled(self, enabled: bool):
        """Enable/disable export controls."""
        self.csv_btn.setEnabled(enabled)
        self.json_btn.setEnabled(enabled)
        self.save_frame_btn.setEnabled(enabled)
        self.export_video_btn.setEnabled(enabled)


class RightPanel(QFrame):
    """
    Right panel with tabbed controls.
    
    Tabs: Overlay, Process, Calibration, Export
    """
    
    # Re-emit signals from child tabs
    overlay_settings_changed = Signal(OverlaySettings)
    run_detection = Signal()
    cancel_detection = Signal()
    preview_requested = Signal(dict)  # Detection params for preview
    params_changed = Signal(dict)  # Current detection params
    tuning_mode_changed = Signal(str)  # "realtime" or "offline"
    calibration_changed = Signal(float)
    recalculate_requested = Signal()
    show_roi_toggled = Signal(bool)
    two_point_mode_changed = Signal(bool)  # For two-point measurement
    roi_adjusted = Signal(int, int, int)  # center_x, center_y, radius
    export_csv = Signal()
    export_json = Signal()
    save_frame = Signal()
    export_video = Signal()
    
    def __init__(self, state_manager: AppStateManager = None, parent=None):
        super().__init__(parent)
        self.state_manager = state_manager
        
        self._setup_ui()
        self._connect_signals()
        self._update_enabled_state(AppState.IDLE)
    
    def _setup_ui(self):
        self.setFixedWidth(DIMENSIONS.RIGHT_PANEL_WIDTH)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            RightPanel {{
                background-color: {COLORS.BG_PANEL};
                border: 1px solid {COLORS.BORDER};
                border-top: none;
                border-bottom: none;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # Create tabs
        self.overlay_tab = OverlayTab()
        self.process_tab = ProcessTab()
        self.calibration_tab = CalibrationTab()
        self.export_tab = ExportTab()
        
        self.tabs.addTab(self.overlay_tab, "Overlay")
        self.tabs.addTab(self.process_tab, "Process")
        self.tabs.addTab(self.calibration_tab, "Calibrate")
        self.tabs.addTab(self.export_tab, "Export")
        
        layout.addWidget(self.tabs)
        
        # Connect tab signals to panel signals
        self.overlay_tab.settings_changed.connect(self.overlay_settings_changed.emit)
        self.process_tab.run_detection.connect(self.run_detection.emit)
        self.process_tab.cancel_detection.connect(self.cancel_detection.emit)
        self.process_tab.preview_requested.connect(self.preview_requested.emit)
        self.process_tab.params_changed.connect(self.params_changed.emit)
        self.process_tab.mode_changed.connect(self.tuning_mode_changed.emit)
        self.calibration_tab.calibration_changed.connect(self.calibration_changed.emit)
        self.calibration_tab.recalculate_requested.connect(self.recalculate_requested.emit)
        self.calibration_tab.show_roi_toggled.connect(self.show_roi_toggled.emit)
        self.calibration_tab.two_point_mode_changed.connect(self.two_point_mode_changed.emit)
        self.calibration_tab.roi_adjusted.connect(self.roi_adjusted.emit)
        self.export_tab.export_csv.connect(self.export_csv.emit)
        self.export_tab.export_json.connect(self.export_json.emit)
        self.export_tab.save_frame.connect(self.save_frame.emit)
        self.export_tab.export_video.connect(self.export_video.emit)
    
    def _connect_signals(self):
        """Connect to state manager."""
        if self.state_manager:
            self.state_manager.state_changed.connect(self._on_state_changed)
            self.state_manager.progress_updated.connect(self._on_progress_updated)
            self.state_manager.cache_changed.connect(self._on_cache_changed)
    
    @Slot(AppState, AppState)
    def _on_state_changed(self, old_state: AppState, new_state: AppState):
        """Update enabled state based on app state."""
        self._update_enabled_state(new_state)
    
    @Slot(int, str)
    def _on_progress_updated(self, percent: int, message: str):
        """Update progress display."""
        self.process_tab.set_progress(percent, message)
        if message:
            self.process_tab.log(message)
    
    @Slot()
    def _on_cache_changed(self, info):
        """Update calibration when cache loads."""
        if info.is_loaded:
            self.calibration_tab.set_calibration(info.px_per_mm)
    
    def _update_enabled_state(self, state: AppState):
        """Enable/disable controls based on app state."""
        can_process = state in (AppState.VIDEO_LOADED, AppState.CACHE_READY)
        can_export = state == AppState.CACHE_READY
        is_processing = state == AppState.PROCESSING
        
        self.process_tab.set_processing(is_processing)
        self.process_tab.set_enabled(can_process or is_processing)
        self.export_tab.set_enabled(can_export)
    
    def get_overlay_settings(self) -> OverlaySettings:
        """Get current overlay settings."""
        return self.overlay_tab.get_settings()
    
    def set_overlay_settings(self, settings: OverlaySettings):
        """Set overlay settings."""
        self.overlay_tab.set_settings(settings)
    
    def set_state_manager(self, manager: AppStateManager):
        """Set or replace state manager."""
        if self.state_manager:
            try:
                self.state_manager.state_changed.disconnect(self._on_state_changed)
                self.state_manager.progress_updated.disconnect(self._on_progress_updated)
                self.state_manager.cache_changed.disconnect(self._on_cache_changed)
            except RuntimeError:
                pass
        
        self.state_manager = manager
        self._connect_signals()
        
        if manager:
            self._update_enabled_state(manager.state)
