"""Programmatically-generated SVG icons for ssl_vista toolbar actions."""

from __future__ import annotations

from PyQt5.QtCore import QByteArray, Qt
from PyQt5.QtGui import QIcon, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer

# ---------------------------------------------------------------------------
# SVG primitives
# ---------------------------------------------------------------------------

_RECORD = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <circle cx="12" cy="12" r="9" fill="#cc2222"/>
</svg>
"""

_STOP_REC = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <rect x="4" y="4" width="16" height="16" rx="2" fill="#cc2222"/>
</svg>
"""

_SCREENSHOT = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="#444444" stroke-width="1.8" stroke-linecap="round">
  <rect x="2" y="6" width="20" height="14" rx="2"/>
  <path d="M8 6 L9.5 3.5 L14.5 3.5 L16 6"/>
  <circle cx="12" cy="13" r="3.5" fill="#444444" stroke="none"/>
</svg>
"""

_PLAY = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M7 4 L20 12 L7 20 Z" fill="#2e7d32"/>
</svg>
"""

_STOP = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <rect x="5" y="5" width="14" height="14" rx="2" fill="#444444"/>
</svg>
"""

_RESET = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="#444444" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="1 4 1 10 7 10"/>
  <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
</svg>
"""

_FILES_MENU = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="#444444" stroke-width="2" stroke-linecap="round">
  <line x1="3" y1="6"  x2="21" y2="6"/>
  <line x1="3" y1="12" x2="21" y2="12"/>
  <line x1="3" y1="18" x2="21" y2="18"/>
</svg>
"""

_SVGS: dict[str, str] = {
    "record": _RECORD,
    "stop_rec": _STOP_REC,
    "screenshot": _SCREENSHOT,
    "play": _PLAY,
    "stop": _STOP,
    "reset": _RESET,
    "files_menu": _FILES_MENU,
}

# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def make_icon(name: str, size: int = 20) -> QIcon:
    """Render a named SVG string into a QIcon.

    Parameters
    ----------
    name:
        One of ``"record"``, ``"stop_rec"``, ``"screenshot"``, ``"play"``, ``"stop"``, ``"reset"``.
    size:
        Icon pixel size (square). Default 20 px.
    """
    svg = _SVGS[name]
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)
