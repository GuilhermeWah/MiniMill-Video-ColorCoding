# MillPresenter V2 — UI Styles

"""
Centralized stylesheet for MillPresenter UI.
Modern, polished dark theme with rounded corners, shadows, and hover effects.
"""

# Color palette (Catppuccin Mocha inspired)
COLORS = {
    # Base colors
    "base": "#1e1e2e",           # Dark background
    "mantle": "#181825",         # Darker background
    "crust": "#11111b",          # Darkest background
    "surface0": "#313244",       # Surface level 0
    "surface1": "#45475a",       # Surface level 1
    "surface2": "#585b70",       # Surface level 2
    
    # Text colors
    "text": "#cdd6f4",           # Primary text
    "subtext0": "#a6adc8",       # Secondary text
    "subtext1": "#bac2de",       # Tertiary text
    "overlay0": "#6c7086",       # Overlay text
    
    # Accent colors
    "blue": "#89b4fa",           # Primary accent
    "green": "#a6e3a1",          # Success
    "yellow": "#f9e2af",         # Warning
    "red": "#f38ba8",            # Error
    "mauve": "#cba6f7",          # Purple accent
    "teal": "#94e2d5",           # Teal accent
    "peach": "#fab387",          # Orange accent
    
    # State colors
    "state_idle": "#6c7086",
    "state_video": "#f9e2af",
    "state_processing": "#89b4fa",
    "state_ready": "#a6e3a1",
}


def get_main_stylesheet() -> str:
    """Get the main application stylesheet."""
    return f"""
    /* ================================================================
       GLOBAL STYLES
       ================================================================ */
    
    QMainWindow {{
        background-color: {COLORS['base']};
    }}
    
    QWidget {{
        color: {COLORS['text']};
        font-family: 'Segoe UI', 'SF Pro Display', sans-serif;
        font-size: 13px;
    }}
    
    /* ================================================================
       MENU BAR
       ================================================================ */
    
    QMenuBar {{
        background-color: {COLORS['mantle']};
        color: {COLORS['text']};
        padding: 4px 8px;
        border-bottom: 1px solid {COLORS['surface0']};
    }}
    
    QMenuBar::item {{
        background-color: transparent;
        padding: 6px 12px;
        border-radius: 4px;
        margin: 2px;
    }}
    
    QMenuBar::item:selected {{
        background-color: {COLORS['surface0']};
    }}
    
    QMenuBar::item:pressed {{
        background-color: {COLORS['surface1']};
    }}
    
    QMenu {{
        background-color: {COLORS['surface0']};
        border: 1px solid {COLORS['surface1']};
        border-radius: 8px;
        padding: 8px;
    }}
    
    QMenu::item {{
        padding: 8px 24px;
        border-radius: 4px;
        margin: 2px;
    }}
    
    QMenu::item:selected {{
        background-color: {COLORS['blue']};
        color: {COLORS['crust']};
    }}
    
    QMenu::separator {{
        height: 1px;
        background-color: {COLORS['surface1']};
        margin: 6px 12px;
    }}
    
    /* ================================================================
       TOOLBAR
       ================================================================ */
    
    QToolBar {{
        background-color: {COLORS['mantle']};
        border: none;
        padding: 8px 12px;
        spacing: 8px;
    }}
    
    QToolBar::separator {{
        width: 1px;
        background-color: {COLORS['surface1']};
        margin: 4px 8px;
    }}
    
    /* ================================================================
       BUTTONS
       ================================================================ */
    
    QPushButton {{
        background-color: {COLORS['surface0']};
        color: {COLORS['text']};
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        min-width: 100px;
    }}
    
    QPushButton:hover {{
        background-color: {COLORS['surface1']};
    }}
    
    QPushButton:pressed {{
        background-color: {COLORS['surface2']};
    }}
    
    QPushButton:disabled {{
        background-color: {COLORS['surface0']};
        color: {COLORS['overlay0']};
    }}
    
    /* Primary button style */
    QPushButton#primary {{
        background-color: {COLORS['blue']};
        color: {COLORS['crust']};
    }}
    
    QPushButton#primary:hover {{
        background-color: #9fc5fc;
    }}
    
    QPushButton#primary:pressed {{
        background-color: #7aa5e8;
    }}
    
    /* ================================================================
       FRAMES
       ================================================================ */
    
    QFrame#videoFrame {{
        background-color: {COLORS['crust']};
        border: 1px solid {COLORS['surface0']};
        border-radius: 12px;
    }}
    
    QFrame#rightPanel {{
        background-color: {COLORS['mantle']};
        border: 1px solid {COLORS['surface0']};
        border-radius: 12px;
    }}
    
    QFrame#bottomBar {{
        background-color: {COLORS['mantle']};
        border-top: 1px solid {COLORS['surface0']};
    }}
    
    /* ================================================================
       LABELS
       ================================================================ */
    
    QLabel {{
        color: {COLORS['text']};
    }}
    
    QLabel#placeholder {{
        color: {COLORS['overlay0']};
        font-size: 16px;
    }}
    
    QLabel#sectionTitle {{
        color: {COLORS['subtext1']};
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    
    /* ================================================================
       STATUS BAR
       ================================================================ */
    
    QStatusBar {{
        background-color: {COLORS['crust']};
        color: {COLORS['subtext0']};
        border-top: 1px solid {COLORS['surface0']};
        padding: 4px 12px;
    }}
    
    /* ================================================================
       SLIDERS
       ================================================================ */
    
    QSlider::groove:horizontal {{
        height: 6px;
        background-color: {COLORS['surface0']};
        border-radius: 3px;
    }}
    
    QSlider::handle:horizontal {{
        background-color: {COLORS['blue']};
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }}
    
    QSlider::handle:horizontal:hover {{
        background-color: #9fc5fc;
    }}
    
    QSlider::sub-page:horizontal {{
        background-color: {COLORS['blue']};
        border-radius: 3px;
    }}
    
    /* ================================================================
       CHECKBOXES
       ================================================================ */
    
    QCheckBox {{
        spacing: 8px;
    }}
    
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid {COLORS['surface2']};
        background-color: transparent;
    }}
    
    QCheckBox::indicator:checked {{
        background-color: {COLORS['blue']};
        border-color: {COLORS['blue']};
    }}
    
    QCheckBox::indicator:hover {{
        border-color: {COLORS['blue']};
    }}
    
    /* ================================================================
       SCROLL BARS
       ================================================================ */
    
    QScrollBar:vertical {{
        background-color: transparent;
        width: 10px;
        margin: 0;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {COLORS['surface1']};
        border-radius: 5px;
        min-height: 30px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {COLORS['surface2']};
    }}
    
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    
    /* ================================================================
       TOOLTIPS
       ================================================================ */
    
    QToolTip {{
        background-color: {COLORS['surface0']};
        color: {COLORS['text']};
        border: 1px solid {COLORS['surface1']};
        border-radius: 6px;
        padding: 6px 10px;
    }}
    
    /* ================================================================
       GROUP BOXES (Collapsible Sections)
       ================================================================ */
    
    QGroupBox {{
        background-color: {COLORS['surface0']};
        border: 1px solid {COLORS['surface1']};
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 12px;
    }}
    
    QGroupBox::title {{
        color: {COLORS['subtext1']};
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 4px 12px;
        font-weight: 600;
    }}
    """


def get_state_pill_style(color: str) -> str:
    """Get styled state pill with gradient and shadow effect."""
    # Lighter version for gradient
    return f"""
        QLabel {{
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 {color}, 
                stop:1 {_darken_color(color, 20)}
            );
            color: {COLORS['crust']};
            font-weight: bold;
            font-size: 11px;
            padding: 6px 16px;
            border-radius: 12px;
            border: 1px solid {_darken_color(color, 10)};
        }}
    """


def _darken_color(hex_color: str, percent: int) -> str:
    """Darken a hex color by a percentage."""
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:], 16)
    factor = 1 - percent / 100
    r, g, b = int(r * factor), int(g * factor), int(b * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


# State-specific pill styles
STATE_PILL_STYLES = {
    "IDLE": get_state_pill_style(COLORS["state_idle"]),
    "VIDEO_LOADED": get_state_pill_style(COLORS["state_video"]),
    "PROCESSING": get_state_pill_style(COLORS["state_processing"]),
    "CACHE_READY": get_state_pill_style(COLORS["state_ready"]),
}
