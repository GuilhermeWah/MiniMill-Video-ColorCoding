"""
MillPresenter Theme Configuration

Centralized visual styling constants for consistent UI appearance.
All colors, dimensions, fonts, and styles defined here.

Design Philosophy:
- Dark theme reduces eye strain during extended use
- High contrast for industrial/laboratory environments
- Color-coded bead classes for instant recognition
- Professional, neutral visual tone
"""

from dataclasses import dataclass
from typing import Dict, Tuple


# =============================================================================
# COLOR PALETTE (Dark Theme)
# =============================================================================

@dataclass(frozen=True)
class Colors:
    """Application color constants."""
    
    # Application chrome
    BG_DARK: str = "#1E1E1E"          # Main window background
    BG_PANEL: str = "#2D2D2D"         # Panel backgrounds
    BG_INPUT: str = "#3C3C3C"         # Input field backgrounds
    BG_HOVER: str = "#404040"         # Hover state
    BG_PRESSED: str = "#505050"       # Pressed state
    
    # Borders and separators
    BORDER: str = "#555555"           # Panel borders
    BORDER_LIGHT: str = "#666666"     # Subtle borders
    SEPARATOR: str = "#404040"        # Divider lines
    
    # Text
    TEXT_PRIMARY: str = "#FFFFFF"     # Primary text
    TEXT_SECONDARY: str = "#AAAAAA"   # Secondary/muted text
    TEXT_DISABLED: str = "#666666"    # Disabled text
    
    # Accent
    ACCENT: str = "#0078D4"           # Primary accent (buttons, selections)
    ACCENT_HOVER: str = "#1084D8"     # Accent hover
    ACCENT_PRESSED: str = "#006CBE"   # Accent pressed
    
    # Status indicators (matching spec exactly)
    STATUS_IDLE: str = "#888888"      # Gray - no video loaded
    STATUS_VIDEO_LOADED: str = "#4A90E2"  # Blue - video loaded, no cache
    STATUS_PROCESSING: str = "#FFA500"    # Orange/Yellow - processing
    STATUS_READY: str = "#2ECC71"         # Green - ready for playback
    STATUS_ERROR: str = "#E74C3C"         # Red - error state


# Bead class colors - consistent across UI and overlays
# Format: (name, hex_color, bgr_tuple for OpenCV)
@dataclass(frozen=True)
class ClassColors:
    """Bead size class colors for overlays and UI indicators."""
    
    # Hex colors for Qt widgets
    MM_4: str = "#0000FF"    # Blue
    MM_6: str = "#00FF00"    # Green  
    MM_8: str = "#FFA500"    # Orange
    MM_10: str = "#FF0000"   # Red
    UNKNOWN: str = "#808080" # Gray
    
    @classmethod
    def get_hex(cls, class_name: str) -> str:
        """Get hex color for a class name."""
        mapping = {
            "4mm": cls.MM_4,
            "6mm": cls.MM_6,
            "8mm": cls.MM_8,
            "10mm": cls.MM_10,
            "unknown": cls.UNKNOWN,
        }
        return mapping.get(class_name, cls.UNKNOWN)
    
    @classmethod
    def get_bgr(cls, class_name: str) -> Tuple[int, int, int]:
        """Get BGR tuple for OpenCV rendering."""
        mapping = {
            "4mm": (255, 0, 0),      # Blue in BGR
            "6mm": (0, 255, 0),      # Green in BGR
            "8mm": (0, 165, 255),    # Orange in BGR
            "10mm": (0, 0, 255),     # Red in BGR
            "unknown": (128, 128, 128),
        }
        return mapping.get(class_name, (128, 128, 128))
    
    @classmethod
    def all_classes(cls) -> list:
        """Return ordered list of all class names."""
        return ["4mm", "6mm", "8mm", "10mm"]


# =============================================================================
# DIMENSIONS
# =============================================================================

@dataclass(frozen=True)
class Dimensions:
    """Layout and sizing constants."""
    
    # Main window
    MIN_WIDTH: int = 1024
    MIN_HEIGHT: int = 700
    DEFAULT_WIDTH: int = 1280
    DEFAULT_HEIGHT: int = 800
    
    # Panel sizes (fixed widths from spec)
    TOP_BAR_HEIGHT: int = 32
    BOTTOM_BAR_HEIGHT: int = 48
    LEFT_PANEL_WIDTH: int = 150
    RIGHT_PANEL_WIDTH: int = 200
    
    # Spacing and padding
    PANEL_PADDING: int = 8
    WIDGET_SPACING: int = 6
    SECTION_SPACING: int = 12
    
    # Widget sizes
    SLIDER_HEIGHT: int = 20
    BUTTON_HEIGHT: int = 28
    CHECKBOX_SIZE: int = 16
    COLOR_DOT_SIZE: int = 12
    ICON_SIZE: int = 16
    
    # Transport controls
    TRANSPORT_BUTTON_SIZE: int = 32
    SCRUBBER_HEIGHT: int = 24


# =============================================================================
# TYPOGRAPHY
# =============================================================================

@dataclass(frozen=True)
class Typography:
    """Font configuration."""
    
    FONT_FAMILY: str = "Segoe UI"
    FONT_FAMILY_MONO: str = "Consolas"
    
    # Font sizes
    SIZE_TITLE: int = 14
    SIZE_LARGE: int = 48      # Total count display
    SIZE_NORMAL: int = 12
    SIZE_SMALL: int = 10
    SIZE_TINY: int = 9


# =============================================================================
# STYLESHEET GENERATOR
# =============================================================================

def get_application_stylesheet() -> str:
    """
    Generate the complete application stylesheet.
    
    Returns a Qt stylesheet string for consistent styling across all widgets.
    """
    c = Colors()
    d = Dimensions()
    t = Typography()
    
    return f"""
    /* ========== Global ========== */
    QWidget {{
        background-color: {c.BG_DARK};
        color: {c.TEXT_PRIMARY};
        font-family: "{t.FONT_FAMILY}";
        font-size: {t.SIZE_NORMAL}pt;
    }}
    
    /* ========== Main Window ========== */
    QMainWindow {{
        background-color: {c.BG_DARK};
    }}
    
    /* ========== Panels ========== */
    QFrame[frameShape="1"] {{
        background-color: {c.BG_PANEL};
        border: 1px solid {c.BORDER};
        border-radius: 4px;
    }}
    
    /* ========== Menu Bar ========== */
    QMenuBar {{
        background-color: {c.BG_PANEL};
        color: {c.TEXT_PRIMARY};
        padding: 2px;
    }}
    
    QMenuBar::item {{
        padding: 4px 8px;
        background-color: transparent;
    }}
    
    QMenuBar::item:selected {{
        background-color: {c.BG_HOVER};
    }}
    
    QMenu {{
        background-color: {c.BG_PANEL};
        border: 1px solid {c.BORDER};
    }}
    
    QMenu::item {{
        padding: 6px 24px;
    }}
    
    QMenu::item:selected {{
        background-color: {c.ACCENT};
    }}
    
    /* ========== Buttons ========== */
    QPushButton {{
        background-color: {c.BG_INPUT};
        border: 1px solid {c.BORDER};
        border-radius: 4px;
        padding: 4px 12px;
        min-height: {d.BUTTON_HEIGHT - 8}px;
    }}
    
    QPushButton:hover {{
        background-color: {c.BG_HOVER};
        border-color: {c.BORDER_LIGHT};
    }}
    
    QPushButton:pressed {{
        background-color: {c.BG_PRESSED};
    }}
    
    QPushButton:disabled {{
        background-color: {c.BG_DARK};
        color: {c.TEXT_DISABLED};
        border-color: {c.SEPARATOR};
    }}
    
    QPushButton[accent="true"] {{
        background-color: {c.ACCENT};
        border-color: {c.ACCENT};
    }}
    
    QPushButton[accent="true"]:hover {{
        background-color: {c.ACCENT_HOVER};
    }}
    
    /* ========== Sliders ========== */
    QSlider::groove:horizontal {{
        height: 4px;
        background: {c.BG_INPUT};
        border-radius: 2px;
    }}
    
    QSlider::handle:horizontal {{
        background: {c.ACCENT};
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    
    QSlider::handle:horizontal:hover {{
        background: {c.ACCENT_HOVER};
    }}
    
    QSlider::sub-page:horizontal {{
        background: {c.ACCENT};
        border-radius: 2px;
    }}
    
    /* ========== Checkboxes ========== */
    QCheckBox {{
        spacing: 6px;
    }}
    
    QCheckBox::indicator {{
        width: {d.CHECKBOX_SIZE}px;
        height: {d.CHECKBOX_SIZE}px;
        border: 1px solid {c.BORDER};
        border-radius: 3px;
        background-color: {c.BG_INPUT};
    }}
    
    QCheckBox::indicator:checked {{
        background-color: {c.ACCENT};
        border-color: {c.ACCENT};
    }}
    
    QCheckBox::indicator:hover {{
        border-color: {c.ACCENT};
    }}
    
    /* ========== Radio Buttons ========== */
    QRadioButton {{
        spacing: 6px;
        color: {c.TEXT_PRIMARY};
    }}
    
    QRadioButton::indicator {{
        width: {d.CHECKBOX_SIZE}px;
        height: {d.CHECKBOX_SIZE}px;
        border: 2px solid {c.BORDER_LIGHT};
        border-radius: {d.CHECKBOX_SIZE // 2}px;
        background-color: {c.BG_INPUT};
    }}
    
    QRadioButton::indicator:checked {{
        background-color: {c.ACCENT};
        border-color: {c.ACCENT};
    }}
    
    QRadioButton::indicator:checked {{
        image: none;
        background-color: {c.ACCENT};
        border: 4px solid {c.BG_INPUT};
        outline: 2px solid {c.ACCENT};
    }}
    
    QRadioButton::indicator:hover {{
        border-color: {c.ACCENT};
    }}
    
    QRadioButton:disabled {{
        color: {c.TEXT_DISABLED};
    }}
    
    QRadioButton::indicator:disabled {{
        border-color: {c.SEPARATOR};
        background-color: {c.BG_DARK};
    }}
    
    /* ========== Group Boxes ========== */
    QGroupBox {{
        border: 1px solid {c.BORDER};
        border-radius: 4px;
        margin-top: 8px;
        padding-top: 8px;
        font-weight: bold;
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 8px;
        padding: 0 4px;
        color: {c.TEXT_SECONDARY};
    }}
    
    /* ========== Tab Widget ========== */
    QTabWidget::pane {{
        border: 1px solid {c.BORDER};
        border-top: none;
        background-color: {c.BG_PANEL};
    }}
    
    QTabBar::tab {{
        background-color: {c.BG_DARK};
        border: 1px solid {c.BORDER};
        border-bottom: none;
        padding: 6px 12px;
        margin-right: 2px;
    }}
    
    QTabBar::tab:selected {{
        background-color: {c.BG_PANEL};
    }}
    
    QTabBar::tab:hover:!selected {{
        background-color: {c.BG_HOVER};
    }}
    
    /* ========== Scroll Bars ========== */
    QScrollBar:vertical {{
        background: {c.BG_DARK};
        width: 12px;
        margin: 0;
    }}
    
    QScrollBar::handle:vertical {{
        background: {c.BG_INPUT};
        min-height: 20px;
        border-radius: 6px;
        margin: 2px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background: {c.BG_HOVER};
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    
    /* ========== Labels ========== */
    QLabel {{
        background-color: transparent;
    }}
    
    QLabel[heading="true"] {{
        font-size: {t.SIZE_TITLE}pt;
        font-weight: bold;
    }}
    
    QLabel[secondary="true"] {{
        color: {c.TEXT_SECONDARY};
    }}
    
    QLabel[large="true"] {{
        font-size: {t.SIZE_LARGE}pt;
        font-weight: bold;
    }}
    
    /* ========== Line Edits ========== */
    QLineEdit {{
        background-color: {c.BG_INPUT};
        border: 1px solid {c.BORDER};
        border-radius: 4px;
        padding: 4px 8px;
    }}
    
    QLineEdit:focus {{
        border-color: {c.ACCENT};
    }}
    
    /* ========== Spin Boxes ========== */
    QSpinBox, QDoubleSpinBox {{
        background-color: {c.BG_INPUT};
        border: 1px solid {c.BORDER};
        border-radius: 4px;
        padding: 4px;
    }}
    
    /* ========== Combo Boxes ========== */
    QComboBox {{
        background-color: {c.BG_INPUT};
        border: 1px solid {c.BORDER};
        border-radius: 4px;
        padding: 4px 8px;
    }}
    
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {c.BG_PANEL};
        border: 1px solid {c.BORDER};
        selection-background-color: {c.ACCENT};
    }}
    
    /* ========== Progress Bar ========== */
    QProgressBar {{
        background-color: {c.BG_INPUT};
        border: 1px solid {c.BORDER};
        border-radius: 4px;
        text-align: center;
        height: 16px;
    }}
    
    QProgressBar::chunk {{
        background-color: {c.ACCENT};
        border-radius: 3px;
    }}
    
    /* ========== Tool Tips ========== */
    QToolTip {{
        background-color: {c.BG_PANEL};
        color: {c.TEXT_PRIMARY};
        border: 1px solid {c.BORDER};
        padding: 4px;
    }}
    
    /* ========== Separators ========== */
    QFrame[frameShape="4"] {{
        background-color: {c.SEPARATOR};
        max-height: 1px;
    }}
    
    QFrame[frameShape="5"] {{
        background-color: {c.SEPARATOR};
        max-width: 1px;
    }}
    """


# =============================================================================
# CONVENIENCE SINGLETONS
# =============================================================================

# Instantiate for easy import
COLORS = Colors()
CLASS_COLORS = ClassColors()
DIMENSIONS = Dimensions()
TYPOGRAPHY = Typography()
