import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath('src'))

print(f"Python executable: {sys.executable}")
print(f"Sys path: {sys.path}")

try:
    import PyQt6
    print(f"PyQt6 imported: {PyQt6}")
    from PyQt6.QtGui import QPainter, QColor, QPen
    print("PyQt6.QtGui imported")
except ImportError as e:
    print(f"Failed to import PyQt6: {e}")

try:
    from mill_presenter.core.overlay import OverlayRenderer
    print(f"OverlayRenderer imported: {OverlayRenderer}")
except ImportError as e:
    print(f"Failed to import OverlayRenderer: {e}")
except Exception as e:
    print(f"Other error importing OverlayRenderer: {e}")
