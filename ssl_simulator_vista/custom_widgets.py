__all__ = [
    "CustomSlider",
    ]

from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QSlider, QVBoxLayout, QWidget, QToolBar, QAction, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer

class CustomSlider(QSlider):
    """Custom slider to shadow key events."""
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)

    def keyPressEvent(self, event):
        """Override key press events to prevent default slider behavior."""
        event.ignore()