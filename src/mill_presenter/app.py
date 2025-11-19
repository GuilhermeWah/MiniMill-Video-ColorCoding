import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel

def main():
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("MillPresenter")
    window.setGeometry(100, 100, 800, 600)
    
    label = QLabel("MillPresenter - Initial Setup Complete", window)
    label.move(50, 50)
    label.resize(400, 50)
    
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
