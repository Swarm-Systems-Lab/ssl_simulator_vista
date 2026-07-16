"""Screenshot and video recording export for ssl_vista."""

from __future__ import annotations

import datetime
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from PIL import Image
from PyQt5.QtCore import QPoint, Qt, QUrl
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from ssl_vista.ui.grid import SimulationGrid

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Format presets
# ---------------------------------------------------------------------------


class ExportFormat(Enum):
    GIF = "gif"
    MP4_HQ = "mp4_hq"
    MP4_SHARE = "mp4_share"
    WEBM = "webm"

    def label(self) -> str:
        return {
            ExportFormat.GIF: "GIF (universal, 256 colours)",
            ExportFormat.MP4_HQ: "MP4 H.264 - HQ (archival, CRF 18)",
            ExportFormat.MP4_SHARE: "MP4 H.264 - Share (web, CRF 28)",
            ExportFormat.WEBM: "WebM VP9 - Small (web)",
        }[self]

    def extension(self) -> str:
        return {
            ExportFormat.GIF: ".gif",
            ExportFormat.MP4_HQ: ".mp4",
            ExportFormat.MP4_SHARE: ".mp4",
            ExportFormat.WEBM: ".webm",
        }[self]

    def needs_ffmpeg(self) -> bool:
        return self in (ExportFormat.MP4_HQ, ExportFormat.MP4_SHARE, ExportFormat.WEBM)


class ImageFormat(Enum):
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"

    def label(self) -> str:
        return {
            ImageFormat.PNG: "PNG (lossless)",
            ImageFormat.JPEG: "JPEG (compressed)",
            ImageFormat.WEBP: "WebP (small)",
        }[self]

    def extension(self) -> str:
        return {ImageFormat.PNG: ".png", ImageFormat.JPEG: ".jpg", ImageFormat.WEBP: ".webp"}[self]

    def pil_format(self) -> str:
        return {ImageFormat.PNG: "PNG", ImageFormat.JPEG: "JPEG", ImageFormat.WEBP: "WEBP"}[self]

    def is_lossy(self) -> bool:
        return self in (ImageFormat.JPEG, ImageFormat.WEBP)


# ---------------------------------------------------------------------------
# Internal capture helpers
# ---------------------------------------------------------------------------


def _pyvista_capture(pvqt: Any) -> np.ndarray:
    """Read pixels directly from a PyVista QtInteractor's VTK render window."""
    img = np.asarray(pvqt.screenshot(return_img=True))
    if img.ndim == 3 and img.shape[2] == 4:
        img = img[:, :, :3]
    return img.copy()


def _mpl_capture(canvas: Any) -> np.ndarray:
    """Read pixels from a matplotlib FigureCanvasQTAgg renderer."""
    canvas.draw()
    buf = canvas.buffer_rgba()
    w, h = canvas.get_width_height()
    rgba = np.frombuffer(buf, dtype=np.uint8).reshape((h, w, 4))
    return rgba[:, :, :3].copy()


def _qt_grab_rgb(widget: QWidget) -> np.ndarray:
    """Fallback Qt-paint capture (misses OpenGL content, use only for non-VTK widgets)."""
    image = widget.grab().toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    h, w = image.height(), image.width()
    ptr = image.constBits()
    assert ptr is not None  # noqa: S101
    ptr.setsize(h * w * 4)  # type: ignore[attr-defined]
    arr = np.frombuffer(ptr.asstring(h * w * 4), dtype=np.uint8).reshape((h, w, 4))  # type: ignore[union-attr]
    return arr[:, :, :3].copy()


def capture_grid(grid: SimulationGrid) -> np.ndarray:
    """Composite all plotter panels into a single (H, W, 3) uint8 RGB image.

    QWidget.grab() misses OpenGL content rendered by PyVista's VTK backend.
    This function uses the native capture path for each plotter type:
    - _BaseVisualPlotter -> pvqt.screenshot(return_img=True) via VTK
    - BaseMplPlotter     -> canvas.buffer_rgba() via matplotlib
    then composites them onto a canvas sized to the full grid widget.
    """
    from ssl_vista.plotters._base_plotters import _BaseVisualPlotter
    from ssl_vista.plotters.base_mpl import BaseMplPlotter

    gw, gh = grid.width(), grid.height()
    canvas = np.zeros((gh, gw, 3), dtype=np.uint8)

    for plotter in grid._plotter_array.flatten():
        if plotter is None:
            continue
        widget = plotter.get_widget()
        pos = widget.mapTo(grid, QPoint(0, 0))
        x, y = pos.x(), pos.y()
        pw, ph = widget.width(), widget.height()

        if isinstance(plotter, _BaseVisualPlotter):
            img = _pyvista_capture(plotter.pvqt)
        elif isinstance(plotter, BaseMplPlotter):
            img = _mpl_capture(plotter.canvas)
        else:
            img = _qt_grab_rgb(widget)

        # Resize to match the widget's displayed size if resolutions differ
        ih, iw = img.shape[:2]
        if ih != ph or iw != pw:
            img = np.array(Image.fromarray(img).resize((pw, ph), Image.Resampling.LANCZOS))

        # Paste into composite canvas, clipping to bounds
        x2, y2 = min(x + pw, gw), min(y + ph, gh)
        if x2 > x and y2 > y:
            canvas[y:y2, x:x2] = img[: y2 - y, : x2 - x]

    return canvas


def _open_writer(imageio_mod, fmt: ExportFormat, path: Path, fps: int):
    """Open an imageio streaming writer for the given format and quality."""
    if fmt == ExportFormat.GIF:
        # GIF duration is per-frame in ms
        return imageio_mod.get_writer(
            str(path), format="GIF", mode="I", loop=0, duration=int(1000 / fps)
        )
    codec = {
        ExportFormat.MP4_HQ: "libx264",
        ExportFormat.MP4_SHARE: "libx264",
        ExportFormat.WEBM: "libvpx-vp9",
    }[fmt]
    extra_params = {
        ExportFormat.MP4_HQ: ["-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p"],
        ExportFormat.MP4_SHARE: ["-crf", "28", "-preset", "fast", "-pix_fmt", "yuv420p"],
        ExportFormat.WEBM: ["-crf", "35", "-b:v", "0", "-pix_fmt", "yuv420p"],
    }[fmt]
    return imageio_mod.get_writer(
        str(path),
        format="FFMPEG",
        mode="I",
        fps=fps,
        codec=codec,
        output_params=extra_params,
    )


# ---------------------------------------------------------------------------
# Internal recording session
# ---------------------------------------------------------------------------


@dataclass
class _RecordingSession:
    writer: Any
    fmt: ExportFormat
    output_path: Path
    fps: int
    frame_count: int = field(default=0, init=False)

    def append(self, frame: np.ndarray) -> None:
        self.writer.append_data(frame)
        self.frame_count += 1

    def close(self) -> None:
        self.writer.close()


# ---------------------------------------------------------------------------
# Recording config dialog
# ---------------------------------------------------------------------------


def _save_dialog(
    parent: QWidget,
    title: str,
    default_path: Path,
    name_filters: list[str],
) -> Path | None:
    """Open a save-file dialog with CWD and Home as sidebar shortcuts.

    Returns the chosen Path, or None if cancelled.
    """
    dlg = QFileDialog(parent, title)
    dlg.setWindowFlags(dlg.windowFlags() | Qt.Window)
    dlg.setAcceptMode(QFileDialog.AcceptSave)
    dlg.setNameFilters(name_filters)
    dlg.setDirectory(str(default_path.parent))
    dlg.selectFile(default_path.name)

    # Build sidebar: existing bookmarks + CWD + Home (dedup by path)
    existing = dlg.sidebarUrls()
    extra = [
        QUrl.fromLocalFile(str(Path.cwd())),
        QUrl.fromLocalFile(str(Path.home())),
    ]
    seen = {url.toLocalFile() for url in existing}
    for url in extra:
        if url.toLocalFile() not in seen:
            existing.append(url)
            seen.add(url.toLocalFile())
    dlg.setSidebarUrls(existing)

    if dlg.exec() != QFileDialog.Accepted:
        return None
    files = dlg.selectedFiles()
    return Path(files[0]) if files else None


def _default_stem() -> str:
    """Return a timestamped filename stem, e.g. 'sslvista_20260701_143000'."""
    return f"sslvista_{datetime.datetime.now():%Y%m%d_%H%M%S}"


def _pictures_dir() -> Path:
    """Return the first existing standard pictures folder, falling back to ~/."""
    home = Path.home()
    for name in ("Pictures", "Images", "Media"):
        p = home / name
        if p.is_dir():
            return p
    return home


def _videos_dir() -> Path:
    """Return the first existing standard videos folder, falling back to ~/."""
    home = Path.home()
    for name in ("Videos", "Movies", "Media"):
        p = home / name
        if p.is_dir():
            return p
    return home


class RecordingConfigDialog(QDialog):
    """Shown before recording starts: choose format, fps, and output path."""

    def __init__(self, default_fps: int, default_stem: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.Window)
        self.setWindowTitle("Start Recording")
        self.setMinimumWidth(460)
        # Pre-populate with a timestamped default in the user's home directory
        default_fmt = ExportFormat.MP4_SHARE
        self._path: Path | None = _videos_dir() / f"{default_stem}{default_fmt.extension()}"

        form = QFormLayout()

        self._fmt = QComboBox()
        for fmt in ExportFormat:
            self._fmt.addItem(fmt.label(), userData=fmt)
        self._fmt.setCurrentIndex(2)  # MP4 Share as default
        form.addRow("Format:", self._fmt)

        self._fps = QSpinBox()
        self._fps.setRange(1, 120)
        self._fps.setValue(default_fps)
        form.addRow("FPS:", self._fps)

        self._path_label = QLabel(str(self._path))
        self._path_label.setWordWrap(True)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self._path_label, stretch=1)
        path_row.addWidget(browse)
        form.addRow("Output:", path_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(buttons)

        self._fmt.currentIndexChanged.connect(self._update_path_ext)

    def _browse(self) -> None:
        fmt: ExportFormat = self._fmt.currentData()
        ext = fmt.extension().lstrip(".")
        default = self._path or _videos_dir() / f"{_default_stem()}{fmt.extension()}"
        result = _save_dialog(
            self,
            "Save Recording As",
            default.with_suffix(fmt.extension()),
            [f"{ext.upper()} Files (*.{ext})", "All Files (*)"],
        )
        if result is not None:
            self._path = result if result.suffix else result.with_suffix(fmt.extension())
            self._path_label.setText(str(self._path))

    def _update_path_ext(self) -> None:
        """Keep path extension consistent when format changes."""
        if self._path is not None:
            self._path = self._path.with_suffix(self._fmt.currentData().extension())
            self._path_label.setText(str(self._path))

    def _on_accept(self) -> None:
        if self._path is None:
            QMessageBox.warning(self, "No Output Selected", "Please choose an output file.")
            return
        self.accept()

    def format(self) -> ExportFormat:
        return self._fmt.currentData()

    def fps(self) -> int:
        return self._fps.value()

    def output_path(self) -> Path:
        return self._path  # type: ignore[return-value]


class ScreenshotConfigDialog(QDialog):
    """Shown before a screenshot is taken: choose image format, quality, and output path."""

    def __init__(self, default_stem: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.Window)
        self.setWindowTitle("Take Screenshot")
        self.setMinimumWidth(460)
        # Pre-populate with a timestamped default in the user's pictures directory
        default_fmt = ImageFormat.PNG
        self._path: Path | None = _pictures_dir() / f"{default_stem}{default_fmt.extension()}"

        form = QFormLayout()

        self._fmt = QComboBox()
        for fmt in ImageFormat:
            self._fmt.addItem(fmt.label(), userData=fmt)
        self._fmt.setCurrentIndex(0)  # PNG as default
        form.addRow("Format:", self._fmt)

        self._quality = QSpinBox()
        self._quality.setRange(1, 100)
        self._quality.setValue(95)
        self._quality.setToolTip("Only used for lossy formats (JPEG, WebP).")
        form.addRow("Quality:", self._quality)

        self._path_label = QLabel(str(self._path))
        self._path_label.setWordWrap(True)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self._path_label, stretch=1)
        path_row.addWidget(browse)
        form.addRow("Output:", path_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(buttons)

        self._fmt.currentIndexChanged.connect(self._on_format_change)
        self._on_format_change()  # sync extension + quality-enabled state

    def _on_format_change(self) -> None:
        """Keep path extension consistent and disable quality for lossless formats."""
        fmt: ImageFormat = self._fmt.currentData()
        self._quality.setEnabled(fmt.is_lossy())
        if self._path is not None:
            self._path = self._path.with_suffix(fmt.extension())
            self._path_label.setText(str(self._path))

    def _browse(self) -> None:
        fmt: ImageFormat = self._fmt.currentData()
        ext = fmt.extension().lstrip(".")
        default = self._path or _pictures_dir() / f"{_default_stem()}{fmt.extension()}"
        result = _save_dialog(
            self,
            "Save Screenshot As",
            default.with_suffix(fmt.extension()),
            [f"{ext.upper()} Images (*.{ext})", "All Files (*)"],
        )
        if result is not None:
            self._path = result if result.suffix else result.with_suffix(fmt.extension())
            self._path_label.setText(str(self._path))

    def _on_accept(self) -> None:
        if self._path is None:
            QMessageBox.warning(self, "No Output Selected", "Please choose an output file.")
            return
        self.accept()

    def format(self) -> ImageFormat:
        return self._fmt.currentData()

    def quality(self) -> int:
        return self._quality.value()

    def output_path(self) -> Path:
        return self._path  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class ExportManager:
    """Screenshot and recording facade owned by MainWindow.

    Parameters
    ----------
    window:
        The parent QMainWindow (used as parent for dialogs).
    get_widget:
        Callable returning the QWidget to capture. Called lazily at capture
        time so the grid can be set after ExportManager is constructed.
    """

    def __init__(self, window: QMainWindow, get_widget: Callable[[], QWidget | None]) -> None:
        self._window = window
        self._get_widget = get_widget
        self._session: _RecordingSession | None = None

    @property
    def is_recording(self) -> bool:
        return self._session is not None

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    def take_screenshot(self) -> None:
        """Show the screenshot config dialog, then capture the current widget state.

        Mirrors the recording flow: a config dialog with a format choice and a
        timestamped default path, followed by a save confirmation.
        """
        widget = self._get_widget()
        if widget is None:
            QMessageBox.warning(self._window, "Nothing to capture", "Load a simulation first.")
            return

        dlg = ScreenshotConfigDialog(_default_stem(), self._window)
        if dlg.exec() != QDialog.Accepted:
            return

        fmt, quality, path = dlg.format(), dlg.quality(), dlg.output_path()

        from ssl_vista.ui.grid import SimulationGrid

        img = capture_grid(widget) if isinstance(widget, SimulationGrid) else _qt_grab_rgb(widget)
        save_kwargs: dict[str, Any] = {"quality": quality} if fmt.is_lossy() else {}
        try:
            Image.fromarray(img).save(str(path), format=fmt.pil_format(), **save_kwargs)
        except Exception as exc:
            QMessageBox.critical(
                self._window, "Screenshot Failed", f"Could not save to:\n{path}\n{exc}"
            )
            return

        _logger.info("Screenshot saved -> %s  (%s)", path, fmt.name)
        QMessageBox.information(self._window, "Screenshot Saved", f"Saved to:\n{path}")

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def start_recording(self, default_fps: int) -> bool:
        """Show config dialog and open the streaming writer.

        Returns True if recording was successfully started, False if the user
        cancelled or a dependency is missing.
        """
        try:
            import imageio
        except ImportError:
            QMessageBox.warning(
                self._window,
                "Missing dependency",
                "Recording requires imageio:\n  uv pip install 'imageio[ffmpeg]'",
            )
            return False

        dlg = RecordingConfigDialog(default_fps, _default_stem(), self._window)
        if dlg.exec() != QDialog.Accepted:
            return False

        fmt, fps, path = dlg.format(), dlg.fps(), dlg.output_path()

        if fmt.needs_ffmpeg():
            try:
                import imageio_ffmpeg  # type: ignore[import-untyped]
            except ImportError:
                QMessageBox.warning(
                    self._window,
                    "Missing dependency",
                    f"{fmt.label()} requires imageio-ffmpeg:\n  uv pip install 'imageio[ffmpeg]'",
                )
                return False

        try:
            writer = _open_writer(imageio, fmt, path, fps)
        except Exception as exc:
            QMessageBox.critical(self._window, "Recording Error", str(exc))
            return False

        self._session = _RecordingSession(writer=writer, fmt=fmt, output_path=path, fps=fps)
        # Lock window size so every frame is the same resolution
        self._window.setFixedSize(self._window.size())
        _logger.info("Recording started -> %s  (%s @ %d fps)", path, fmt.name, fps)
        return True

    def capture_frame(self) -> None:
        """Append the current widget state as the next recording frame.

        Call this once per rendered frame (e.g. inside update_simulation).
        No-op when not recording or when the capture widget is unavailable.
        """
        if self._session is None:
            return
        widget = self._get_widget()
        if widget is None:
            return
        from ssl_vista.ui.grid import SimulationGrid

        frame = capture_grid(widget) if isinstance(widget, SimulationGrid) else _qt_grab_rgb(widget)
        self._session.append(frame)

    def stop_recording(self) -> None:
        """Flush and close the writer, then show a confirmation dialog."""
        if self._session is None:
            return
        session, self._session = self._session, None
        session.close()
        # Restore normal resizing behaviour
        self._window.setMinimumSize(0, 0)
        self._window.setMaximumSize(16777215, 16777215)  # QWIDGETSIZE_MAX
        _logger.info("Recording stopped: %d frames -> %s", session.frame_count, session.output_path)
        QMessageBox.information(
            self._window,
            "Recording Saved",
            f"{session.frame_count} frames saved to:\n{session.output_path}",
        )
