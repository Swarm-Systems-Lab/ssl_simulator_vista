from pathlib import Path

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAction,
    QFileDialog,
    QLabel,
    QMenu,
    QToolBar,
    QToolButton,
)

from .custom_widgets import CustomSlider
from .icons import make_icon


class SimulationToolbar(QToolBar):
    """Toolbar for simulation controls."""

    # Signals so parent window can handle these events
    sim_file_loaded = pyqtSignal(str)
    grid_layout_requested = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__("Simulation Controls", parent)
        self.setMovable(True)
        self.sim_file_path = None
        self.grid_file_path = None
        self._last_csv_dir = str(Path.cwd())
        self._last_grid_dir = str(Path.cwd())

        font = QFont()
        font.setPointSize(12)
        self.setFont(font)

        # ------------------------------------------------------------------
        # Files menu button (hamburger)
        # ------------------------------------------------------------------
        self.load_grid_action = QAction("Load Grid Layout", self)
        self.load_csv_action = QAction("Load CSV", self)
        self.reload_csv_action = QAction("Reload CSV", self)

        files_menu = QMenu(self)
        files_menu.addAction(self.load_grid_action)
        files_menu.addSeparator()
        files_menu.addAction(self.load_csv_action)
        files_menu.addAction(self.reload_csv_action)

        self.files_button = QToolButton(self)
        self.files_button.setIcon(make_icon("files_menu"))
        self.files_button.setToolTip("Files")
        self.files_button.setMenu(files_menu)
        self.files_button.setPopupMode(QToolButton.InstantPopup)
        self.addWidget(self.files_button)

        self.addSeparator()

        # ------------------------------------------------------------------
        # Playback controls
        # ------------------------------------------------------------------
        self.play_action = QAction(make_icon("play"), "Play", self)
        self.stop_action = QAction(make_icon("stop"), "Stop", self)
        self.reset_action = QAction(make_icon("reset"), "Reset", self)
        self.addActions([self.play_action, self.stop_action, self.reset_action])

        self.addSeparator()

        # ------------------------------------------------------------------
        # Time slider
        # ------------------------------------------------------------------
        self.time_label = QLabel("Time: 0.00 ")
        self.addWidget(self.time_label)

        self.time_slider = CustomSlider(Qt.Horizontal, self)
        self.time_slider.setRange(0, 100)  # Placeholder range
        self.addWidget(self.time_slider)

        self.addSeparator()

        # ------------------------------------------------------------------
        # View controls
        # ------------------------------------------------------------------
        self.reset_view_action = QAction(make_icon("reset_view"), "Reset View", self)
        self.addAction(self.reset_view_action)

        self.addSeparator()

        # ------------------------------------------------------------------
        # Export controls
        # ------------------------------------------------------------------
        self.screenshot_action = QAction(make_icon("screenshot"), "Screenshot", self)
        self.record_action = QAction(make_icon("record"), "Record", self)
        self.addAction(self.screenshot_action)
        self.addAction(self.record_action)

        # ------------------------------------------------------------------
        # Connections
        # ------------------------------------------------------------------
        self.load_csv_action.triggered.connect(self._on_load_file)
        self.load_grid_action.triggered.connect(self._on_load_grid_layout)

    # ----------------------------------------------------------------------
    # METHODS
    # ----------------------------------------------------------------------
    def _on_load_file(self):
        """Prompt user to load a simulation data CSV file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Simulation File", self._last_csv_dir, "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return

        self._last_csv_dir = str(Path(file_path).parent)
        self.sim_file_path = file_path
        self.sim_file_loaded.emit(file_path)

    def _on_load_grid_layout(self):
        """Prompt the user to select a grid layout file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Grid Layout File",
            self._last_grid_dir,
            "Layout Files (*.json *.yaml *.yml);;All Files (*)",
        )
        if not file_path:
            return

        self._last_grid_dir = str(Path(file_path).parent)
        self.grid_file_path = file_path
        self.grid_layout_requested.emit(file_path)
