"""
Left Panel Widget

Statistics display panel showing real-time detection metrics.

Layout:
┌────────────┐
│ Stats|Info │  (Tab toggle)
├────────────┤
│ Total:     │
│   342      │  (Large number)
├────────────┤
│ By Class:  │
│ ● 4mm: 85  │
│ ● 6mm: 120 │
│ ● 8mm: 95  │
│ ● 10mm: 42 │
├────────────┤
│ Confidence │
│  ▁▂▅▇▅▂▁   │  (Histogram)
├────────────┤
│ Running Avg│
│  ╱╲╱╲╱╲    │  (Line graph)
└────────────┘

HCI Principles Applied:
- Visibility (Nielsen #1): Live stats always visible during playback
- Recognition (Nielsen #6): Color-coded class indicators match overlays
- Aesthetic & Minimalist (Nielsen #8): Only essential stats shown
"""

from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Slot, QSize
from PySide6.QtGui import QFont, QPainter, QColor, QPen

from ui.theme import COLORS, DIMENSIONS, TYPOGRAPHY, CLASS_COLORS
from ui.state import AppState, AppStateManager


class ClassCountWidget(QWidget):
    """Single class count display with colored dot."""
    
    def __init__(self, class_name: str, parent=None):
        super().__init__(parent)
        self.class_name = class_name
        self._count = 0
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(6)
        
        # Color dot
        self.dot = QLabel("●")
        color = CLASS_COLORS.get_hex(self.class_name)
        self.dot.setStyleSheet(f"color: {color}; font-size: 12px;")
        self.dot.setFixedWidth(16)
        layout.addWidget(self.dot)
        
        # Class label
        self.label = QLabel(f"{self.class_name}:")
        self.label.setProperty("secondary", True)
        layout.addWidget(self.label)
        
        # Count
        self.count_label = QLabel("0")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.count_label, stretch=1)
    
    def set_count(self, count: int):
        """Update the count display."""
        self._count = count
        self.count_label.setText(str(count))
    
    @property
    def count(self) -> int:
        return self._count


class TotalCountWidget(QWidget):
    """Large total bead count display."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Label
        self.label = QLabel("Total Beads")
        self.label.setProperty("secondary", True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        # Large count number
        self.count = QLabel("0")
        self.count.setProperty("large", True)
        self.count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont(TYPOGRAPHY.FONT_FAMILY, TYPOGRAPHY.SIZE_LARGE)
        font.setBold(True)
        self.count.setFont(font)
        layout.addWidget(self.count)
    
    def set_count(self, count: int):
        """Update the total count."""
        self.count.setText(str(count))


class MiniHistogram(QWidget):
    """
    Small confidence distribution histogram.
    
    Displays a bar chart of confidence values bucketed into bins.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bins = [0] * 10  # 10 bins for 0.0-1.0
        self.setMinimumHeight(40)
        self.setMaximumHeight(60)
    
    def set_distribution(self, bins: list):
        """Set histogram bins (list of counts per bin)."""
        self._bins = bins[:10] if len(bins) >= 10 else bins + [0] * (10 - len(bins))
        self.update()
    
    def paintEvent(self, event):
        """Draw the histogram."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Background
        painter.fillRect(0, 0, w, h, QColor(COLORS.BG_INPUT))
        
        # Draw bars
        if not self._bins or max(self._bins) == 0:
            painter.end()
            return
        
        max_val = max(self._bins)
        bar_width = (w - 4) / len(self._bins)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(COLORS.ACCENT))
        
        for i, val in enumerate(self._bins):
            bar_height = (val / max_val) * (h - 8) if max_val > 0 else 0
            x = 2 + i * bar_width
            y = h - 4 - bar_height
            painter.drawRect(int(x), int(y), int(bar_width - 1), int(bar_height))
        
        painter.end()


class MiniLineGraph(QWidget):
    """
    Small running average line graph.
    
    Shows count stability over recent frames.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = []
        self._max_points = 30
        self.setMinimumHeight(40)
        self.setMaximumHeight(60)
    
    def add_value(self, value: float):
        """Add a new value to the graph."""
        self._values.append(value)
        if len(self._values) > self._max_points:
            self._values.pop(0)
        self.update()
    
    def clear(self):
        """Clear all values."""
        self._values = []
        self.update()
    
    def paintEvent(self, event):
        """Draw the line graph."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Background
        painter.fillRect(0, 0, w, h, QColor(COLORS.BG_INPUT))
        
        if len(self._values) < 2:
            painter.end()
            return
        
        # Calculate scaling
        min_val = min(self._values)
        max_val = max(self._values)
        val_range = max_val - min_val if max_val != min_val else 1
        
        # Draw line
        pen = QPen(QColor(COLORS.ACCENT))
        pen.setWidth(2)
        painter.setPen(pen)
        
        points = []
        for i, val in enumerate(self._values):
            x = 4 + (i / (self._max_points - 1)) * (w - 8)
            y = h - 4 - ((val - min_val) / val_range) * (h - 8)
            points.append((int(x), int(y)))
        
        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], 
                           points[i+1][0], points[i+1][1])
        
        painter.end()


class StatsTab(QWidget):
    """Statistics display tab."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # Total count
        self.total_widget = TotalCountWidget()
        layout.addWidget(self.total_widget)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)
        
        # By class section
        class_label = QLabel("By Class")
        class_label.setProperty("secondary", True)
        layout.addWidget(class_label)
        
        # Class counts
        self.class_widgets = {}
        for cls in CLASS_COLORS.all_classes():
            widget = ClassCountWidget(cls)
            self.class_widgets[cls] = widget
            layout.addWidget(widget)
        
        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep2)
        
        # Confidence histogram
        conf_label = QLabel("Confidence Distribution")
        conf_label.setProperty("secondary", True)
        layout.addWidget(conf_label)
        
        self.histogram = MiniHistogram()
        layout.addWidget(self.histogram)
        
        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep3)
        
        # Running average graph
        avg_label = QLabel("Running Average")
        avg_label.setProperty("secondary", True)
        layout.addWidget(avg_label)
        
        self.line_graph = MiniLineGraph()
        layout.addWidget(self.line_graph)
        
        # Spacer
        layout.addStretch(1)
    
    def update_stats(self, total: int, by_class: dict, conf_bins: list = None):
        """Update all statistics displays."""
        self.total_widget.set_count(total)
        
        for cls, widget in self.class_widgets.items():
            count = by_class.get(cls, 0)
            widget.set_count(count)
        
        if conf_bins:
            self.histogram.set_distribution(conf_bins)
        
        # Add to running average
        self.line_graph.add_value(total)


class InfoTab(QWidget):
    """Video information display tab."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        title = QLabel("Video Info")
        title.setProperty("heading", True)
        layout.addWidget(title)
        
        # Info grid
        grid = QGridLayout()
        grid.setSpacing(4)
        
        self._labels = {}
        fields = [
            ("Resolution", "resolution"),
            ("FPS", "fps"),
            ("Duration", "duration"),
            ("Total Frames", "frames"),
            ("Calibration", "px_per_mm"),
        ]
        
        for i, (label, key) in enumerate(fields):
            lbl = QLabel(f"{label}:")
            lbl.setProperty("secondary", True)
            grid.addWidget(lbl, i, 0)
            
            val = QLabel("-")
            self._labels[key] = val
            grid.addWidget(val, i, 1)
        
        layout.addLayout(grid)
        layout.addStretch(1)
    
    def set_video_info(self, width: int, height: int, fps: float, 
                       total_frames: int, px_per_mm: float = None):
        """Update video info display."""
        self._labels["resolution"].setText(f"{width}×{height}")
        self._labels["fps"].setText(f"{fps:.1f}")
        
        duration = total_frames / fps if fps > 0 else 0
        mins = int(duration) // 60
        secs = int(duration) % 60
        self._labels["duration"].setText(f"{mins}:{secs:02d}")
        self._labels["frames"].setText(str(total_frames))
        
        if px_per_mm:
            self._labels["px_per_mm"].setText(f"{px_per_mm:.2f} px/mm")
        else:
            self._labels["px_per_mm"].setText("-")


class LeftPanel(QFrame):
    """
    Left panel containing statistics and video info tabs.
    
    Fixed width, can be hidden/shown.
    """
    
    def __init__(self, state_manager: AppStateManager = None, parent=None):
        super().__init__(parent)
        self.state_manager = state_manager
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        self.setFixedWidth(DIMENSIONS.LEFT_PANEL_WIDTH)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            LeftPanel {{
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
        
        self.stats_tab = StatsTab()
        self.info_tab = InfoTab()
        
        self.tabs.addTab(self.stats_tab, "Stats")
        self.tabs.addTab(self.info_tab, "Info")
        
        layout.addWidget(self.tabs)
    
    def _connect_signals(self):
        """Connect to state manager."""
        if self.state_manager:
            self.state_manager.video_changed.connect(self._on_video_changed)
            self.state_manager.cache_changed.connect(self._on_cache_changed)
    
    @Slot()
    def _on_video_changed(self, info):
        """Update info tab when video changes."""
        if info.is_loaded:
            self.info_tab.set_video_info(
                info.width, info.height, info.fps,
                info.total_frames
            )
    
    @Slot()
    def _on_cache_changed(self, info):
        """Update calibration info when cache loads."""
        if info.is_loaded:
            # Update px_per_mm display
            self.info_tab._labels["px_per_mm"].setText(
                f"{info.px_per_mm:.2f} px/mm"
            )
    
    def update_stats(self, total: int, by_class: dict, conf_bins: list = None):
        """Update statistics display."""
        self.stats_tab.update_stats(total, by_class, conf_bins)
    
    def set_state_manager(self, manager: AppStateManager):
        """Set or replace state manager."""
        if self.state_manager:
            try:
                self.state_manager.video_changed.disconnect(self._on_video_changed)
                self.state_manager.cache_changed.disconnect(self._on_cache_changed)
            except RuntimeError:
                pass
        
        self.state_manager = manager
        self._connect_signals()
