# MillPresenter — Production UI (Final)
# Fixes: Better icons, fullscreen state badge, stats contrast

"""
Final fixes applied:
1. Better playback icons (filled variants, not outline Unicode)
2. Fullscreen state badge overlay in corner
3. Stats values brighter when cache ready
"""

import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStatusBar, QLabel, QPushButton, QFileDialog, 
    QFrame, QSizePolicy, QSlider, QCheckBox, QComboBox,
    QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, Signal, Slot, QThread

from mill_presenter.ui.state_manager import StateManager, AppState
from mill_presenter.ui.video_widget import VideoWidget
from mill_presenter.ui.playback_controller import PlaybackController
from mill_presenter.ui.overlay_painter import OverlayWidget
from mill_presenter.ui.detection_worker import DetectionWorker
from mill_presenter.ui.calibration_controller import CalibrationController
from mill_presenter.core.frame_loader import FrameLoader
from mill_presenter.utils import config


# ============================================================================
# DESIGN TOKENS
# ============================================================================

C = {
    "void": "#08080c",
    "bg": "#12121a",
    "surface": "#1a1a24",
    "elevated": "#22222e",
    "border": "#2a2a38",
    "muted": "#4a4a5e",
    "dim": "#6a6a82",
    "subtle": "#8a8aa6",
    "text": "#b0b0c8",
    "bright": "#d0d0e8",
    "white": "#e8e8f4",
    "accent": "#7aa2f7",
    "green": "#9ece6a",
    "yellow": "#e0af68",
    "red": "#f7768e",
}

FONT = "Segoe UI, system-ui, sans-serif"

CLASS_COLORS = {
    4: ("#9ece6a", "4mm"),
    6: ("#7aa2f7", "6mm"),
    8: ("#e0af68", "8mm"),
    10: ("#f7768e", "10mm"),
}

# Better transport icons (filled, consistent)
ICONS = {
    "prev": "⏮",      # Previous
    "play": "▶",      # Play (filled triangle)
    "pause": "⏸",     # Pause
    "next": "⏭",      # Next
    "fs": "⛶",        # Fullscreen
}


def css(size: int, weight: int, color: str) -> str:
    return f"font-family:{FONT};font-size:{size}px;font-weight:{weight};color:{color};line-height:1.5;"


# ============================================================================
# COMPONENTS
# ============================================================================

class StatePill(QLabel):
    """State indicator."""
    
    def __init__(self, compact: bool = False):
        super().__init__()
        self._compact = compact
        self.setAlignment(Qt.AlignCenter)
        self._set("NO VIDEO", C['muted'])
    
    def _set(self, text: str, bg: str) -> None:
        self.setText(text)
        size = 11 if self._compact else 13
        pad = "4px 10px" if self._compact else "6px 16px"
        radius = 10 if self._compact else 14
        self.setStyleSheet(f"""
            background: {bg}; color: {C['void']};
            {css(size, 700, C['void'])}
            padding: {pad}; border-radius: {radius}px;
        """)
    
    def set_state(self, s: AppState) -> None:
        m = {
            AppState.IDLE: ("NO VIDEO", C['muted']),
            AppState.VIDEO_LOADED: ("NO CACHE", C['yellow']),
            AppState.PROCESSING: ("PROCESSING", C['accent']),
            AppState.CACHE_READY: ("READY", C['green']),
        }
        self._set(*m.get(s, ("—", C['muted'])))
    
    def set_progress(self, p: int) -> None:
        self._set(f"{p}%", C['accent'])


class EmptyState(QWidget):
    """Empty state overlay."""
    
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)
        
        self.icon = QLabel("◇")
        self.icon.setStyleSheet(f"font-size: 48px; color: {C['accent']};")
        self.icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon)
        
        self.title = QLabel("Open a video to begin")
        self.title.setStyleSheet(css(17, 600, C['bright']))
        self.title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title)
        
        self.subtitle = QLabel("Drag & drop or use File → Open Video")
        self.subtitle.setStyleSheet(css(13, 400, C['dim']))
        self.subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.subtitle)
        
        self.hint = QLabel("")
        self.hint.setStyleSheet(css(12, 400, C['muted']))
        self.hint.setAlignment(Qt.AlignCenter)
        self.hint.hide()
        layout.addWidget(self.hint)
    
    def update_state(self, s: AppState) -> None:
        m = {
            AppState.IDLE: ("◇", C['accent'], "Open a video to begin", "Drag & drop or use File → Open Video", ""),
            AppState.VIDEO_LOADED: ("◈", C['yellow'], "Cache required", "Run Preprocessor or Load Cache to enable overlays.", "Playback available. Overlays disabled."),
            AppState.PROCESSING: ("◎", C['accent'], "Processing...", "Analyzing frames. Please wait.", ""),
            AppState.CACHE_READY: ("", "", "", "", ""),
        }
        icon, color, title, sub, hint = m.get(s, m[AppState.IDLE])
        
        self.icon.setText(icon)
        self.icon.setStyleSheet(f"font-size: 48px; color: {color};")
        self.title.setText(title)
        self.subtitle.setText(sub)
        
        if hint:
            self.hint.setText(hint)
            self.hint.show()
        else:
            self.hint.hide()
        
        self.setVisible(s != AppState.CACHE_READY)


class Divider(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(1)
        self.setStyleSheet(f"background: {C['border']}; margin: 8px 0;")


class ControlPanel(QFrame):
    """Right panel."""
    
    class_toggled = Signal(int, bool)
    confidence_changed = Signal(float)
    speed_changed = Signal(float)
    
    def __init__(self):
        super().__init__()
        self.setFixedWidth(190)
        self.setStyleSheet(f"background:{C['bg']};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(0)
        
        self.ctrl = QWidget()
        ctrl_l = QVBoxLayout(self.ctrl)
        ctrl_l.setContentsMargins(0, 0, 0, 0)
        ctrl_l.setSpacing(0)
        
        # VISIBILITY
        ctrl_l.addWidget(self._header("VISIBILITY", primary=True))
        ctrl_l.addSpacing(10)
        
        self.cbs = {}
        for cid, (color, name) in CLASS_COLORS.items():
            cb = QCheckBox(f"● {name}")
            cb.setChecked(True)
            cb.setStyleSheet(f"""
                QCheckBox {{ {css(13, 500, color)} spacing: 8px; }}
                QCheckBox::indicator {{ width: 14px; height: 14px; border: 2px solid {C['muted']}; border-radius: 3px; }}
                QCheckBox::indicator:checked {{ background: {color}; border-color: {color}; }}
                QCheckBox:disabled {{ color: {C['muted']}; }}
            """)
            cb.toggled.connect(lambda v, c=cid: self.class_toggled.emit(c, v))
            self.cbs[cid] = cb
            ctrl_l.addWidget(cb)
            ctrl_l.addSpacing(2)
        
        ctrl_l.addSpacing(14)
        ctrl_l.addWidget(Divider())
        ctrl_l.addSpacing(14)
        
        # FILTER
        ctrl_l.addWidget(self._header("FILTER"))
        ctrl_l.addSpacing(10)
        
        row = QHBoxLayout()
        row.setSpacing(10)
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(50)
        self.slider.setMinimumHeight(28)
        self.slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ height: 6px; background: {C['muted']}; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: {C['accent']}; width: 18px; height: 18px; margin: -6px 0; border-radius: 9px; }}
            QSlider::sub-page:horizontal {{ background: {C['accent']}; border-radius: 3px; }}
            QSlider:disabled::handle:horizontal {{ background: {C['muted']}; }}
        """)
        self.slider.valueChanged.connect(self._on_conf)
        
        self.conf_val = QLabel("≥ 0.50")
        self.conf_val.setStyleSheet(f"{css(14, 700, C['accent'])} min-width: 55px;")
        
        row.addWidget(self.slider, 1)
        row.addWidget(self.conf_val)
        ctrl_l.addLayout(row)
        
        ctrl_l.addSpacing(8)
        micro = QLabel("Display only. Does not re-run detection.")
        micro.setStyleSheet(css(11, 400, C['subtle']))
        ctrl_l.addWidget(micro)
        
        ctrl_l.addSpacing(16)
        ctrl_l.addWidget(Divider())
        ctrl_l.addSpacing(16)
        
        # STATS (brighter values when active)
        ctrl_l.addWidget(self._header("STATS", muted=True))
        ctrl_l.addSpacing(8)
        
        self.stats = {}
        self.stat_val_labels = {}
        for key, name in [("total", "Total"), (4, "4mm"), (6, "6mm"), (8, "8mm"), (10, "10mm")]:
            row = QHBoxLayout()
            row.setSpacing(0)
            
            lbl = QLabel(name)
            lbl.setStyleSheet(css(12, 400, C['dim']))
            
            val = QLabel("—")
            val.setStyleSheet(css(13, 600, C['muted']))
            val.setAlignment(Qt.AlignRight)
            self.stats[key] = val
            
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            ctrl_l.addLayout(row)
            ctrl_l.addSpacing(3)
        
        ctrl_l.addSpacing(16)
        ctrl_l.addWidget(Divider())
        ctrl_l.addSpacing(14)
        
        # PLAYBACK
        ctrl_l.addWidget(self._header("PLAYBACK", muted=True))
        ctrl_l.addSpacing(8)
        
        row = QHBoxLayout()
        lbl = QLabel("Speed")
        lbl.setStyleSheet(css(12, 400, C['dim']))
        
        self.speed = QComboBox()
        self.speed.addItems(["0.25×", "0.5×", "1×"])
        self.speed.setCurrentIndex(2)
        self.speed.setToolTip("Playback speed only. Detection unchanged.")
        self.speed.setStyleSheet(f"""
            QComboBox {{ background: {C['elevated']}; color: {C['text']}; border: none; padding: 6px 12px; border-radius: 4px; {css(12, 500, C['text'])} min-width: 60px; }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox:disabled {{ color: {C['muted']}; background: {C['bg']}; }}
        """)
        self.speed.currentTextChanged.connect(lambda t: self.speed_changed.emit(float(t.replace("×", ""))))
        
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(self.speed)
        ctrl_l.addLayout(row)
        
        ctrl_l.addStretch()
        layout.addWidget(self.ctrl)
        
        self.set_enabled(False)
    
    def _header(self, text: str, primary: bool = False, muted: bool = False) -> QLabel:
        lbl = QLabel(text)
        if primary:
            lbl.setStyleSheet(f"{css(14, 700, C['white'])} letter-spacing: 1.5px;")
        elif muted:
            lbl.setStyleSheet(f"{css(11, 600, C['dim'])} letter-spacing: 1px;")
        else:
            lbl.setStyleSheet(f"{css(13, 600, C['text'])} letter-spacing: 1px;")
        return lbl
    
    def _on_conf(self, v: int) -> None:
        c = v / 100.0
        self.conf_val.setText(f"≥ {c:.2f}")
        self.confidence_changed.emit(c)
    
    def set_enabled(self, e: bool) -> None:
        for cb in self.cbs.values():
            cb.setEnabled(e)
            cb.setToolTip("" if e else "Requires cache")
        
        self.slider.setEnabled(e)
        self.slider.setToolTip("" if e else "Requires cache")
        self.speed.setEnabled(e)
        
        eff = QGraphicsOpacityEffect()
        eff.setOpacity(1.0 if e else 0.4)
        self.ctrl.setGraphicsEffect(eff if not e else None)
    
    def _on_conf(self, val: int) -> None:
        """Handle confidence slider change."""
        conf = val / 100.0
        self.conf_val.setText(f"≥ {conf:.2f}")
        self.confidence_changed.emit(conf)
    
    def update_stats(self, total: int, by_class: dict) -> None:
        # Brighter values when data is present
        self.stats["total"].setText(str(total))
        self.stats["total"].setStyleSheet(css(13, 700, C['white']))
        for c in [4, 6, 8, 10]:
            self.stats[c].setText(str(by_class.get(c, 0)))
            self.stats[c].setStyleSheet(css(13, 600, C['bright']))


class TransportBar(QFrame):
    """Playback bar with combined play/pause, speed selector, and zoom controls."""
    
    play = Signal()
    pause = Signal()
    fullscreen = Signal()
    speed_changed = Signal(float)
    zoom_changed = Signal(float)  # Emits zoom level (1.0 = 100%)
    
    def __init__(self):
        super().__init__()
        self.setFixedHeight(56)
        self.setStyleSheet(f"background:{C['surface']}; border-radius: 0px;")
        self._playing = False
        self._zoom_level = 1.0
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(0)
        
        # LEFT: Transport controls
        left = QHBoxLayout()
        left.setSpacing(6)
        
        # Step buttons (smaller, secondary)
        step_css = f"""
            QPushButton {{
                background: {C['elevated']}; color: {C['text']};
                border: none; border-radius: 8px;
                font-size: 14px;
                min-width: 34px; max-width: 34px;
                min-height: 34px; max-height: 34px;
            }}
            QPushButton:hover {{ background: {C['muted']}; }}
            QPushButton:disabled {{ color: {C['muted']}; background: {C['bg']}; }}
        """
        
        # Combined play/pause button
        play_css = f"""
            QPushButton {{
                background: {C['accent']}; color: {C['bg']};
                border: none; border-radius: 10px;
                font-size: 18px;
                min-width: 44px; max-width: 44px;
                min-height: 44px; max-height: 44px;
            }}
            QPushButton:hover {{ background: #8ab4ff; }}
            QPushButton:disabled {{ color: {C['muted']}; background: {C['bg']}; }}
        """
        
        # Previous frame
        self.prev_btn = QPushButton(ICONS["prev"])
        self.prev_btn.setStyleSheet(step_css)
        self.prev_btn.setToolTip("Previous frame (←)")
        left.addWidget(self.prev_btn)
        
        # Combined play/pause toggle
        self.play_pause_btn = QPushButton(ICONS["play"])
        self.play_pause_btn.setStyleSheet(play_css)
        self.play_pause_btn.setToolTip("Play/Pause (Space)")
        self.play_pause_btn.clicked.connect(self._toggle_play)
        left.addWidget(self.play_pause_btn)
        
        # Next frame
        self.next_btn = QPushButton(ICONS["next"])
        self.next_btn.setStyleSheet(step_css)
        self.next_btn.setToolTip("Next frame (→)")
        left.addWidget(self.next_btn)
        
        # Speed selector
        left.addSpacing(12)
        
        speed_combo_css = f"""
            QComboBox {{
                background: {C['elevated']}; color: {C['text']};
                border: none; border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px; font-weight: 600;
                min-width: 60px;
            }}
            QComboBox:hover {{ background: {C['muted']}; }}
            QComboBox::drop-down {{ border: none; width: 16px; }}
            QComboBox::down-arrow {{ image: none; }}
            QComboBox QAbstractItemView {{
                background: {C['elevated']}; color: {C['text']};
                selection-background-color: {C['accent']};
                border: 1px solid {C['border']};
                border-radius: 6px;
            }}
        """
        self.speed_combo = QComboBox()
        self.speed_combo.setStyleSheet(speed_combo_css)
        for speed in [0.1, 0.125, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0]:
            self.speed_combo.addItem(f"{speed}×", speed)
        self.speed_combo.setCurrentIndex(4)  # Default 1.0×
        self.speed_combo.currentIndexChanged.connect(self._on_speed_changed)
        left.addWidget(self.speed_combo)
        
        layout.addLayout(left)
        layout.addSpacing(24)
        
        # CENTER: Scrubber + Timecode
        center = QHBoxLayout()
        center.setSpacing(14)
        
        self.scrubber = QSlider(Qt.Horizontal)
        self.scrubber.setRange(0, 1000)
        self.scrubber.setMinimumHeight(32)
        self.scrubber.setStyleSheet(f"""
            QSlider::groove:horizontal {{ height: 8px; background: {C['border']}; border-radius: 4px; }}
            QSlider::handle:horizontal {{ background: {C['white']}; width: 18px; height: 18px; margin: -5px 0; border-radius: 9px; }}
            QSlider::handle:horizontal:hover {{ background: #ffffff; }}
            QSlider::sub-page:horizontal {{ background: {C['accent']}; border-radius: 4px; }}
            QSlider:disabled::handle:horizontal {{ background: {C['muted']}; }}
        """)
        center.addWidget(self.scrubber, 1)
        
        self.timecode = QLabel("00:00.000 / 00:00.000")
        self.timecode.setStyleSheet(f"{css(14, 600, C['text'])} min-width: 150px;")
        center.addWidget(self.timecode)
        
        layout.addLayout(center, 1)
        layout.addSpacing(24)
        
        # RIGHT: Zoom controls
        right = QHBoxLayout()
        right.setSpacing(6)
        
        zoom_btn_css = f"""
            QPushButton {{
                background: {C['elevated']}; color: {C['text']};
                border: none; border-radius: 6px;
                font-size: 14px; font-weight: 600;
                min-width: 32px; max-width: 32px;
                min-height: 32px; max-height: 32px;
            }}
            QPushButton:hover {{ background: {C['muted']}; color: {C['bright']}; }}
            QPushButton:disabled {{ color: {C['muted']}; background: {C['bg']}; }}
        """
        
        zoom_pct_css = f"""
            QPushButton {{
                background: {C['elevated']}; color: {C['text']};
                border: none; border-radius: 6px;
                font-size: 12px; font-weight: 600;
                padding: 6px 10px;
                min-width: 54px;
            }}
            QPushButton:hover {{ background: {C['muted']}; color: {C['bright']}; }}
        """
        
        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.setStyleSheet(zoom_btn_css)
        self.zoom_out_btn.setToolTip("Zoom out")
        self.zoom_out_btn.clicked.connect(lambda: self._adjust_zoom(-0.25))
        right.addWidget(self.zoom_out_btn)
        
        self.zoom_pct_btn = QPushButton("100%")
        self.zoom_pct_btn.setStyleSheet(zoom_pct_css)
        self.zoom_pct_btn.setToolTip("Click to fit window")
        self.zoom_pct_btn.clicked.connect(self._fit_zoom)
        right.addWidget(self.zoom_pct_btn)
        
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setStyleSheet(zoom_btn_css)
        self.zoom_in_btn.setToolTip("Zoom in")
        self.zoom_in_btn.clicked.connect(lambda: self._adjust_zoom(0.25))
        right.addWidget(self.zoom_in_btn)
        
        right.addSpacing(8)
        
        self.fs_btn = QPushButton(ICONS["fs"])
        self.fs_btn.setStyleSheet(zoom_btn_css)
        self.fs_btn.setToolTip("Fullscreen (F). Esc to exit.")
        self.fs_btn.clicked.connect(self.fullscreen)
        right.addWidget(self.fs_btn)
        
        layout.addLayout(right)
        
        # Keep references to step buttons for external connection
        self.btns = [self.prev_btn, self.play_pause_btn, self.next_btn]
    
    def _toggle_play(self) -> None:
        """Toggle play/pause state."""
        if self._playing:
            self.pause.emit()
        else:
            self.play.emit()
    
    def set_playing(self, playing: bool) -> None:
        """Update button icon based on play state."""
        self._playing = playing
        self.play_pause_btn.setText(ICONS["pause"] if playing else ICONS["play"])
    
    def _on_speed_changed(self, index: int) -> None:
        speed = self.speed_combo.itemData(index)
        self.speed_changed.emit(speed)
    
    def _adjust_zoom(self, delta: float) -> None:
        """Adjust zoom by delta, clamped to valid range."""
        new_zoom = max(0.25, min(4.0, self._zoom_level + delta))
        if new_zoom != self._zoom_level:
            self._zoom_level = new_zoom
            self._update_zoom_display()
            self.zoom_changed.emit(new_zoom)
        # Disable zoom out at minimum
        self.zoom_out_btn.setEnabled(self._zoom_level > 0.25)
    
    def _fit_zoom(self) -> None:
        """Fit to window (sets zoom to 'fit' mode)."""
        self._zoom_level = 1.0
        self._update_zoom_display()
        self.zoom_changed.emit(0.0)  # 0.0 signals 'fit to window'
    
    def _update_zoom_display(self) -> None:
        pct = int(self._zoom_level * 100)
        self.zoom_pct_btn.setText(f"{pct}%")
    
    def set_zoom_level(self, level: float) -> None:
        """Called externally to sync zoom display."""
        self._zoom_level = level
        self._update_zoom_display()
        self.zoom_out_btn.setEnabled(level > 0.25)
    
    def set_enabled(self, e: bool) -> None:
        for b in self.btns:
            b.setEnabled(e)
        self.scrubber.setEnabled(e)
    
    def update_position(self, frame: int, total: int, time_s: float, total_s: float) -> None:
        if total > 0:
            self.scrubber.setValue(int(frame * 1000 / total))
        def fmt(s): return f"{int(s // 60):02d}:{s % 60:06.3f}"
        self.timecode.setText(f"{fmt(time_s)} / {fmt(total_s)}")
    
    def set_speed(self, s: float) -> None:
        # Find matching index
        for i in range(self.speed_combo.count()):
            if self.speed_combo.itemData(i) == s:
                self.speed_combo.setCurrentIndex(i)
                break


class FullscreenStateBadge(QLabel):
    """Compact state badge for fullscreen mode overlay."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self._pill = StatePill(compact=True)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._pill)
        
        self.setStyleSheet("background: transparent;")
        self.hide()
    
    def set_state(self, s: AppState) -> None:
        self._pill.set_state(s)
    
    def set_progress(self, p: int) -> None:
        self._pill.set_progress(p)


class MainWindow(QMainWindow):
    """Main window with fullscreen state badge."""
    
    video_opened = Signal(str)
    run_requested = Signal()
    cache_loaded = Signal()
    
    def __init__(self):
        super().__init__()
        self.sm = StateManager(self)
        self._fs = False
        self._loader: Optional[FrameLoader] = None
        self._cache_data: Optional[Dict[str, Any]] = None
        self._current_frame = 0
        self._frame_iterator = None  # For sequential playback
        self._last_sequential_frame = -1  # Track last frame from iterator
        
        # Playback controller
        self.playback = PlaybackController(self)
        self.playback.set_frame_callback(self._on_playback_frame)
        self.playback.position_changed.connect(self._on_position_changed)
        
        # Overlay painter for detection circles
        self._overlay = OverlayWidget()
        
        # Detection worker (background thread)
        self._detection_thread: Optional[QThread] = None
        self._detection_worker: Optional[DetectionWorker] = None
        self._video_path_for_detection: Optional[str] = None
        
        # Calibration controller
        self._calibration = CalibrationController(self)
        self._calibration.calibration_complete.connect(self._on_calibration_complete)
        self._calibration.point_added.connect(self._on_calibration_point)
        self._calibration.calibration_cancelled.connect(self._on_calibration_cancelled)
        
        self._build()
        self._connect()
        self._on_state(AppState.IDLE, AppState.IDLE)
    
    def _build(self) -> None:
        self.setWindowTitle("MillPresenter")
        self.setMinimumSize(1000, 650)
        self.resize(1200, 800)
        self.setStyleSheet(f"QMainWindow{{background:{C['void']};}}")
        
        # TOP BAR
        self.top_bar = QFrame()
        self.top_bar.setFixedHeight(48)
        self.top_bar.setStyleSheet(f"background:{C['surface']};")
        
        top_l = QHBoxLayout(self.top_bar)
        top_l.setContentsMargins(20, 0, 20, 0)
        top_l.setSpacing(0)
        
        name_group = QHBoxLayout()
        name_group.setSpacing(8)
        
        name = QLabel("MillPresenter")
        name.setStyleSheet(css(14, 600, C['dim']))
        name_group.addWidget(name)
        
        self.pill = StatePill()
        name_group.addWidget(self.pill)
        
        top_l.addLayout(name_group)
        top_l.addStretch()
        
        btn_css = f"""
            QPushButton {{ background: {C['elevated']}; {css(13, 500, C['text'])} border: none; padding: 8px 18px; border-radius: 6px; }}
            QPushButton:hover {{ background: {C['muted']}; }}
            QPushButton:disabled {{ background: {C['bg']}; color: {C['muted']}; }}
        """
        btn_primary = f"""
            QPushButton {{ background: {C['accent']}; {css(13, 700, C['void'])} border: none; padding: 8px 18px; border-radius: 6px; }}
            QPushButton:hover {{ background: #8ab4f8; }}
            QPushButton:disabled {{ background: {C['muted']}; color: {C['dim']}; }}
        """
        
        self.btn_open = QPushButton("Open Video")
        self.btn_open.setStyleSheet(btn_css)
        self.btn_open.clicked.connect(self._open)
        top_l.addWidget(self.btn_open)
        
        top_l.addSpacing(12)
        
        self.btn_run = QPushButton("Run Preprocessor")
        self.btn_run.setStyleSheet(btn_css)
        self.btn_run.clicked.connect(self._run)
        top_l.addWidget(self.btn_run)
        
        top_l.addSpacing(8)
        
        self.btn_load = QPushButton("Load Cache")
        self.btn_load.setStyleSheet(btn_css)
        self.btn_load.clicked.connect(self._load)
        top_l.addWidget(self.btn_load)
        
        top_l.addSpacing(8)
        
        self.btn_calibrate = QPushButton("Calibrate")
        self.btn_calibrate.setStyleSheet(btn_css)
        self.btn_calibrate.clicked.connect(self._start_calibration)
        self.btn_calibrate.setToolTip("Click two points on a known distance to calibrate")
        top_l.addWidget(self.btn_calibrate)
        
        self.btn_clear_cal = QPushButton("Clear Cal")
        self.btn_clear_cal.setStyleSheet(btn_css)
        self.btn_clear_cal.clicked.connect(self._clear_calibration)
        self.btn_clear_cal.setToolTip("Clear manual calibration and use auto drum detection")
        top_l.addWidget(self.btn_clear_cal)
        
        self._btn_css = btn_css
        self._btn_primary = btn_primary
        
        # CENTRAL
        central = QWidget()
        self.setCentralWidget(central)
        
        main_l = QVBoxLayout(central)
        main_l.setContentsMargins(0, 0, 0, 0)
        main_l.setSpacing(0)
        
        main_l.addWidget(self.top_bar)
        main_l.addWidget(self._sep_h())
        
        content = QHBoxLayout()
        content.setSpacing(0)
        
        # Canvas with VideoWidget
        self.canvas = QWidget()
        self.canvas.setStyleSheet(f"background:{C['void']};")
        
        canvas_l = QVBoxLayout(self.canvas)
        canvas_l.setContentsMargins(0, 0, 0, 0)
        canvas_l.setSpacing(0)
        
        # Video widget (actual frame display)
        self.video_widget = VideoWidget()
        self.video_widget.zoom_changed.connect(self._on_video_zoom_changed)
        self.video_widget.frame_clicked.connect(self._handle_video_click)
        canvas_l.addWidget(self.video_widget, 1)
        
        # Empty state overlay (floats on top)
        self.empty = EmptyState()
        self.empty.setParent(self.canvas)
        
        content.addWidget(self.canvas, 1)
        content.addWidget(self._sep_v())
        
        # Panel
        self.panel = ControlPanel()
        self.panel.speed_changed.connect(self._on_speed)
        self.panel.class_toggled.connect(self._on_class_toggled)
        self.panel.confidence_changed.connect(self._on_confidence_changed)
        content.addWidget(self.panel)
        
        main_l.addLayout(content, 1)
        main_l.addWidget(self._sep_h())
        
        # Transport
        self.transport = TransportBar()
        self.transport.fullscreen.connect(self._toggle_fs)
        # Connect zoom - new signal-based approach
        self.transport.zoom_changed.connect(self._on_transport_zoom)
        # Connect speed selector
        self.transport.speed_changed.connect(self._on_speed)
        # Connect playback controls (combined play/pause now)
        self.transport.play.connect(self._start_playback)
        self.transport.pause.connect(self._stop_playback)
        self.transport.prev_btn.clicked.connect(self._step_backward)
        self.transport.next_btn.clicked.connect(self._step_forward)
        # Connect scrubber - use sliderReleased to avoid lag during drag
        self.transport.scrubber.sliderReleased.connect(self._on_scrubber_released)
        self.transport.scrubber.sliderPressed.connect(self._stop_playback)
        main_l.addWidget(self.transport)
        
        # Fullscreen state badge (overlays in corner)
        self.fs_badge = FullscreenStateBadge(self)
        self.fs_badge.move(20, 20)
        
        # Status
        self.status = QStatusBar()
        self.status.setStyleSheet(f"QStatusBar {{ background: {C['void']}; {css(11, 400, C['dim'])} }} QStatusBar::item {{ border: none; }}")
        self.status.setFixedHeight(24)
        self.setStatusBar(self.status)
    
    def _sep_h(self) -> QFrame:
        s = QFrame()
        s.setFixedHeight(1)
        s.setStyleSheet(f"background:{C['border']};")
        return s
    
    def _sep_v(self) -> QFrame:
        s = QFrame()
        s.setFixedWidth(1)
        s.setStyleSheet(f"background:{C['border']};")
        return s
    
    def _connect(self) -> None:
        self.sm.state_changed.connect(self._on_state)
        self.sm.progress_updated.connect(self._on_progress)
    
    @Slot(AppState, AppState)
    def _on_state(self, old: AppState, new: AppState) -> None:
        self.pill.set_state(new)
        self.fs_badge.set_state(new)
        self.empty.update_state(new)
        
        run_ok = self.sm.is_action_allowed("run_detection")
        self.btn_run.setEnabled(run_ok)
        self.btn_run.setStyleSheet(self._btn_primary if run_ok else self._btn_css)
        self.btn_run.setToolTip("" if run_ok else (self.sm.get_disabled_reason("run_detection") or ""))
        
        self.btn_load.setEnabled(self.sm.is_action_allowed("load_cache"))
        self.panel.set_enabled(new == AppState.CACHE_READY)
        self.transport.set_enabled(self.sm.is_action_allowed("playback"))
        self.status.showMessage(self.sm.state_info.description)
    
    @Slot(int, str)
    def _on_progress(self, p: int, msg: str) -> None:
        self.pill.set_progress(p)
        self.fs_badge.set_progress(p)
        self.status.showMessage(msg or f"Processing... {p}%")
    
    def _on_speed(self, s: float) -> None:
        self.transport.set_speed(s)
        self.playback.set_speed(s)
    
    def _on_class_toggled(self, class_mm: int, visible: bool) -> None:
        """Handle class visibility toggle."""
        # Update VideoWidget's overlay filter (no frame refresh needed - just repaint)
        self.video_widget.set_class_visible(class_mm, visible)
    
    def _on_confidence_changed(self, confidence: float) -> None:
        """Handle confidence threshold change."""
        # Update VideoWidget's confidence filter (no frame refresh needed - just repaint)
        self.video_widget.set_min_confidence(confidence)
    
    def _start_playback(self) -> None:
        """Start playback and update transport button."""
        self.playback.play()
        self.transport.set_playing(True)
    
    def _stop_playback(self) -> None:
        """Stop playback and update transport button."""
        self.playback.pause()
        self.transport.set_playing(False)
    
    def _step_forward(self) -> None:
        """Step forward one frame."""
        self.playback.step_forward()
    
    def _step_backward(self) -> None:
        """Step backward one frame."""
        self.playback.step_backward()
    
    def _on_transport_zoom(self, level: float) -> None:
        """Handle zoom change from transport bar."""
        if level == 0.0:
            # Fit to window
            self.video_widget.zoom_fit()
        else:
            self.video_widget.set_zoom(level)
    
    def _on_video_zoom_changed(self, level: float) -> None:
        """Sync transport bar zoom display when video widget zoom changes."""
        self.transport.set_zoom_level(level)
    
    def _open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Video", "", "Videos (*.mov *.mp4 *.avi *.mkv);;All (*)")
        if path:
            # Close any existing loader
            if self._loader:
                self._loader.close()
            
            try:
                self._loader = FrameLoader(path)
                self._current_frame = 0
                self.sm.set_video_loaded(path)
                self.video_opened.emit(path)
                self.status.showMessage(f"{Path(path).name} — {self._loader.total_frames} frames @ {self._loader.fps:.1f} fps")
                
                # Configure playback controller
                self.playback.set_video_info(
                    self._loader.total_frames,
                    self._loader.fps,
                    self._loader.duration
                )
                
                # Reset speed to 1.0x and sync UI
                self.playback.set_speed(1.0)
                self.transport.set_speed(1.0)
                
                # Initialize frame iterator for sequential playback
                self._frame_iterator = self._loader.iter_frames(0)
                self._last_sequential_frame = -1
                
                # Show first frame
                self._show_frame(0)
                
            except Exception as e:
                self.status.showMessage(f"Error: {e}")
    
    def _run(self) -> None:
        """Run detection pipeline in background thread."""
        if not self.sm.is_action_allowed("run_detection"):
            return
        
        if not self._loader:
            self.status.showMessage("No video loaded")
            return
        
        # Generate cache path next to video
        video_path = str(self._loader._path)
        cache_path = str(Path(video_path).with_suffix('.detections.json'))
        self._video_path_for_detection = video_path
        
        # Start processing state
        self.sm.set_processing_started()
        self.run_requested.emit()
        
        # Create worker and thread
        self._detection_thread = QThread()
        self._detection_worker = DetectionWorker(video_path, cache_path)
        self._detection_worker.moveToThread(self._detection_thread)
        
        # Connect signals
        self._detection_thread.started.connect(self._detection_worker.run)
        self._detection_worker.progress.connect(self._on_detection_progress)
        self._detection_worker.finished.connect(self._on_detection_finished)
        
        # Start
        self._detection_thread.start()
    
    @Slot(int, int, str)
    def _on_detection_progress(self, current: int, total: int, msg: str) -> None:
        """Handle detection progress update."""
        pct = int(100 * current / max(1, total))
        self.pill.set_progress(pct)
        self.fs_badge.set_progress(pct)
        self.status.showMessage(msg)
    
    @Slot(bool, str)
    def _on_detection_finished(self, success: bool, result: str) -> None:
        """Handle detection completion."""
        # Clean up thread
        if self._detection_thread:
            self._detection_thread.quit()
            self._detection_thread.wait()
            self._detection_thread = None
            self._detection_worker = None
        
        if success:
            # Auto-load the cache
            cache_path = result
            try:
                with open(cache_path, 'r') as f:
                    self._cache_data = json.load(f)
                
                # Set overlay cache
                self._overlay.set_cache(self._cache_data)
                
                # Initialize frame iterator
                self._frame_iterator = self._loader.iter_frames(0)
                self._last_sequential_frame = -1
                
                # Show first frame with overlays
                self._show_frame(0)
                
                self.sm.set_cache_ready(cache_path)
                self.cache_loaded.emit()
                self.status.showMessage(f"Detection complete: {Path(cache_path).name}")
                
                # Update stats
                self._update_stats_for_frame(0)
                
            except Exception as e:
                self.status.showMessage(f"Error loading cache: {e}")
                self.sm.set_video_loaded(self._video_path_for_detection)
        else:
            self.status.showMessage(f"Detection failed: {result}")
            if self._video_path_for_detection:
                self.sm.set_video_loaded(self._video_path_for_detection)
    
    def _load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load Cache", "", "JSON (*.json)")
        if path:
            try:
                with open(path, 'r') as f:
                    self._cache_data = json.load(f)
                
                # Get video path from cache metadata
                video_path = self._cache_data.get('metadata', {}).get('video_path')
                
                # Set overlay cache for detection circles
                self._overlay.set_cache(self._cache_data)
                
                # If we don't have a loader or it's a different video, load it
                if video_path and (not self._loader or str(self._loader._path) != video_path):
                    if self._loader:
                        self._loader.close()
                    self._loader = FrameLoader(video_path)
                    self._current_frame = 0
                    
                    # Configure playback controller
                    self.playback.set_video_info(
                        self._loader.total_frames,
                        self._loader.fps,
                        self._loader.duration
                    )
                    
                    # Initialize frame iterator
                    self._frame_iterator = self._loader.iter_frames(0)
                    self._last_sequential_frame = -1
                
                # Show first frame with overlays
                self._show_frame(0)
                
                self.sm.set_cache_ready(path)
                self.cache_loaded.emit()
                self.status.showMessage(Path(path).name)
                
                # Update stats from cache
                self._update_stats_for_frame(0)
                
            except Exception as e:
                self.status.showMessage(f"Error loading cache: {e}")
    
    def _show_frame(self, frame_idx: int) -> None:
        """Display a specific frame in the video widget."""
        if not self._loader:
            return
        
        try:
            # Use sequential iterator if frame is ahead of last read (for playback with skipping)
            if (self._frame_iterator is not None and 
                frame_idx > self._last_sequential_frame):
                # Read frames sequentially until we reach the target
                try:
                    frame = None
                    while self._last_sequential_frame < frame_idx:
                        idx, frame = next(self._frame_iterator)
                        self._last_sequential_frame = idx
                except StopIteration:
                    self._frame_iterator = None
                    frame = self._loader.get_frame(frame_idx)
            else:
                # Backward seek or random access - use get_frame
                frame = self._loader.get_frame(frame_idx)
                # Reset iterator at new position for future sequential reads
                self._frame_iterator = self._loader.iter_frames(frame_idx + 1)
                self._last_sequential_frame = frame_idx
            
            # Display frame
            self.video_widget.set_frame(frame)
            self._current_frame = frame_idx
            
            # Set overlays for this frame (drawn by VideoWidget with Qt)
            if self._cache_data:
                detections = self._overlay._frame_lookup.get(frame_idx, [])
                self.video_widget.set_overlays(detections)
            
            # Hide empty state when showing video
            self.empty.hide()
            
        except Exception as e:
            self.status.showMessage(f"Frame error: {e}")
    
    def _update_stats_for_frame(self, frame_idx: int) -> None:
        """Update stats panel for current frame."""
        if not self._cache_data:
            return
        
        frames = self._cache_data.get('frames', {})
        
        # Handle dict format (keys are string frame IDs)
        if isinstance(frames, dict):
            frame_data = frames.get(str(frame_idx))
            if frame_data:
                balls = frame_data.get('balls', [])
                total = len(balls)
                by_class = {4: 0, 6: 0, 8: 0, 10: 0}
                for ball in balls:
                    size = ball.get('cls', ball.get('class_mm', 0))  # 'cls' in Ball model
                    if size in by_class:
                        by_class[size] += 1
                self.panel.update_stats(total, by_class)
                return
        # Handle list format (legacy)
        elif isinstance(frames, list):
            for frame_data in frames:
                if frame_data.get('frame_index', frame_data.get('frame_id')) == frame_idx:
                    detections = frame_data.get('detections', frame_data.get('balls', []))
                    total = len(detections)
                    by_class = {4: 0, 6: 0, 8: 0, 10: 0}
                    for det in detections:
                        size = det.get('cls', det.get('class_mm', 0))
                        if size in by_class:
                            by_class[size] += 1
                    self.panel.update_stats(total, by_class)
                    return
        
        # No data for this frame
        self.panel.update_stats(0, {})
    
    def _on_playback_frame(self, frame_idx: int) -> None:
        """Called by PlaybackController when frame changes during playback."""
        self._show_frame(frame_idx)
        if self._cache_data:
            self._update_stats_for_frame(frame_idx)
    
    def _on_position_changed(self, frame: int, total: int, time_s: float, duration_s: float) -> None:
        """Called by PlaybackController when position changes."""
        self.transport.update_position(frame, total, time_s, duration_s)
        # Update scrubber without triggering sliderMoved
        self.transport.scrubber.blockSignals(True)
        if total > 0:
            self.transport.scrubber.setValue(int(1000 * frame / max(1, total - 1)))
        self.transport.scrubber.blockSignals(False)
    
    def _on_scrubber_released(self) -> None:
        """Called when user releases the scrubber."""
        value = self.transport.scrubber.value()
        position = value / 1000.0
        
        if self._loader:
            # Fast seek - use keyframe approximation (max 30 frames decode)
            target_frame = int(position * (self._loader.total_frames - 1))
            try:
                frame = self._loader.get_frame(target_frame, max_decode=30)
                self.video_widget.set_frame(frame)
                self._current_frame = target_frame
                self._last_sequential_frame = target_frame
                # Reset iterator for future sequential reads
                self._frame_iterator = self._loader.iter_frames(target_frame + 1)
                self.empty.hide()
                # Update playback position
                self.playback.seek_to_frame(target_frame)
            except Exception as e:
                self.status.showMessage(f"Seek error: {e}")
    
    def _toggle_fs(self) -> None:
        if self._fs:
            self.showNormal()
            self.panel.show()
            self.top_bar.show()
            self.fs_badge.hide()
            self._fs = False
        else:
            self.showFullScreen()
            self.panel.hide()
            self.top_bar.hide()
            self.fs_badge.show()
            self.fs_badge.raise_()
            self._fs = True
    
    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        # Keep fullscreen badge in top-left
        self.fs_badge.move(20, 20)
        # Center empty state overlay
        if hasattr(self, 'empty') and hasattr(self, 'canvas'):
            self.empty.move(
                (self.canvas.width() - self.empty.width()) // 2,
                (self.canvas.height() - self.empty.height()) // 2
            )
    
    def _on_zoom_changed(self, zoom: float) -> None:
        """Handle zoom level change from VideoWidget."""
        # Update transport bar zoom display if needed
        pass
    
    def keyPressEvent(self, e) -> None:
        if e.key() == Qt.Key_Escape and self._fs:
            self._toggle_fs()
        elif e.key() == Qt.Key_F:
            self._toggle_fs()
        elif e.key() == Qt.Key_Space and self.sm.is_action_allowed("playback"):
            self.playback.toggle_play_pause()
        elif e.key() == Qt.Key_Left and self.sm.is_action_allowed("playback"):
            self.playback.step_backward()
        elif e.key() == Qt.Key_Right and self.sm.is_action_allowed("playback"):
            self.playback.step_forward()
        elif e.key() == Qt.Key_Home and self.sm.is_action_allowed("playback"):
            self.playback.seek_to_frame(0)
        elif e.key() == Qt.Key_End and self.sm.is_action_allowed("playback"):
            self.playback.seek_to_frame(self.playback._total_frames - 1)
        elif e.key() == Qt.Key_Escape and self._calibration.is_active:
            self._calibration.cancel()
        else:
            super().keyPressEvent(e)
    
    def mouseDoubleClickEvent(self, e) -> None:
        if self.canvas.geometry().contains(e.pos()):
            self._toggle_fs()
        super().mouseDoubleClickEvent(e)
    
    # ========================================================================
    # Calibration
    # ========================================================================
    
    def _start_calibration(self) -> None:
        """Enter calibration mode."""
        if not self._loader:
            self.status.showMessage("Load a video first to calibrate")
            return
        
        self._calibration.start()
        self.btn_calibrate.setStyleSheet(self._btn_primary)
        self.btn_calibrate.setText("Calibrating...")
        self.status.showMessage("Click two points on a known distance (press Esc to cancel)")
    
    def _on_calibration_complete(self, px_per_mm: float) -> None:
        """Handle completed calibration."""
        # Save to config
        config.set_calibration(px_per_mm)
        
        # Update UI
        self.btn_calibrate.setStyleSheet(self._btn_css)
        self.btn_calibrate.setText("Calibrate")
        self.status.showMessage(f"Calibration complete: {px_per_mm:.4f} px/mm — Re-run detection to apply")
        
        # Clear calibration overlay
        self.video_widget.set_calibration_points([])
    
    def _on_calibration_point(self, x: int, y: int) -> None:
        """Handle calibration point added."""
        # Update overlay to show calibration markers
        points = self._calibration.points
        self.video_widget.set_calibration_points(points)
        
        if len(points) == 1:
            self.status.showMessage(f"Point 1: ({x}, {y}) — Click second point")
    
    def _on_calibration_cancelled(self) -> None:
        """Handle calibration cancellation."""
        self.btn_calibrate.setStyleSheet(self._btn_css)
        self.btn_calibrate.setText("Calibrate")
        self.status.showMessage("Calibration cancelled")
        self.video_widget.set_calibration_points([])
    
    def _handle_video_click(self, x: int, y: int) -> None:
        """Handle click on video widget (for calibration)."""
        print(f"[MAIN_WINDOW] Click received: ({x}, {y}), calibration_active={self._calibration.is_active}")
        if self._calibration.is_active:
            self._calibration.handle_click(x, y)
    
    def _clear_calibration(self) -> None:
        """Clear manual calibration and revert to auto mode."""
        config.clear_calibration()
        self.status.showMessage("Manual calibration cleared — will use auto drum detection")


def main():
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
