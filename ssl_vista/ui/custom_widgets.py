__all__ = [
    "CustomSlider",
    ]

from PyQt5.QtWidgets import QSlider

class CustomSlider(QSlider):
    """Custom slider to shadow key events."""
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)

    def keyPressEvent(self, event):
        """Override key press events to prevent default slider behavior."""
        event.ignore()