__all__ = [
    "SimulationToolbar",
    ]

from PyQt5.QtWidgets import QToolBar, QAction, QLabel, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal

from custom_widgets import CustomSlider

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

        # ------------------------------------------------------------------
        # File loading actions
        # ------------------------------------------------------------------
        self.load_csv_action = QAction("Load CSV", self)
        self.reload_csv_action = QAction("Reload CSV", self)
        self.load_grid_action = QAction("Load Grid Layout", self)

        self.addAction(self.load_grid_action)
        self.addSeparator()
        self.addAction(self.load_csv_action)
        self.addAction(self.reload_csv_action)

        self.addSeparator()

        # ------------------------------------------------------------------
        # Playback controls
        # ------------------------------------------------------------------
        self.play_action = QAction("Play", self)
        self.stop_action = QAction("Stop", self)
        self.reset_action = QAction("Reset", self)
        self.addActions([self.play_action, self.stop_action, self.reset_action])

        self.addSeparator()

        # ------------------------------------------------------------------
        # Time slider
        # ------------------------------------------------------------------
        self.time_label = QLabel("Time: 0.00")
        self.addWidget(self.time_label)

        self.time_slider = CustomSlider(Qt.Horizontal, self)
        self.time_slider.setRange(0, 100)  # Placeholder range
        self.addWidget(self.time_slider)

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
            self,
            "Select Simulation File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return

        self.sim_file_path = file_path
        self.sim_file_loaded.emit(file_path)

        # QMessageBox.information(self, "File Loaded",
        #                         f"Simulation file selected:\n{file_path}")
             
    def _on_load_grid_layout(self):
        """Prompt the user to select a grid layout file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Grid Layout File",
            "",
            "Layout Files (*.json *.yaml *.yml);;All Files (*)"
        )
        if not file_path:
            return

        self.grid_file_path = file_path
        self.grid_layout_requested.emit(file_path)
        # QMessageBox.information(self, "Grid Layout Loaded",
        #                         f"Grid layout file selected:\n{file_path}")