from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import numpy as np
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from ssl_simulator.utils.processing import load_sim

from .export import ExportManager
from .grid import SimulationGrid, load_grid_from_json
from .icons import make_icon
from .toolbars import SimulationToolbar

if TYPE_CHECKING:
    from ssl_vista.types import SimData, SimSettings

_logger = logging.getLogger(__name__)

# For Wayland compatibility (e.g. Ubuntu)
os.environ["QT_QPA_PLATFORM"] = "xcb"


class MainWindow(QMainWindow):
    """Base simulation application with a toolbar and customizable grid layout."""

    def __init__(
        self,
        title: str = "Simulation Viewer",
        layout: str | None = None,
        data_path: str | None = None,
        auto_play: bool = False,
        width_ratio: float = 0.8,
        height_ratio: float = 0.8,
        animation_period: int = 40,
        # --- Programmatic path ---
        grid: SimulationGrid | None = None,
        sim_data: SimData | None = None,
        sim_settings: SimSettings | None = None,
    ):
        super().__init__()
        self.setWindowTitle(title)
        self.auto_play = auto_play
        self.animation_period = animation_period  # in ms

        # --- Set initial window size and position ---
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()  # Excludes taskbar/dock
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        width = int(screen_width * width_ratio)
        height = int(screen_height * height_ratio)
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.setGeometry(x, y, width, height)

        # --- Toolbar ---
        self.simulation_toolbar = SimulationToolbar(self)
        self.addToolBar(self.simulation_toolbar)
        self.simulation_toolbar.setFocusPolicy(Qt.StrongFocus)

        # Connect toolbar actions
        self.time_slider = self.simulation_toolbar.time_slider
        self.time_label = self.simulation_toolbar.time_label

        self.simulation_toolbar.sim_file_loaded.connect(self.load_csv)
        self.simulation_toolbar.grid_layout_requested.connect(self.load_grid_layout)
        self.simulation_toolbar.reload_csv_action.triggered.connect(self.reload_csv)
        self.simulation_toolbar.play_action.triggered.connect(self.play_simulation)
        self.simulation_toolbar.stop_action.triggered.connect(self.stop_simulation)
        self.simulation_toolbar.reset_action.triggered.connect(self.reset_simulation)
        self.simulation_toolbar.time_slider.valueChanged.connect(self.update_time)
        self.simulation_toolbar.time_slider.sliderPressed.connect(self.slider_pressed)
        self.simulation_toolbar.time_slider.blockSignals(True)
        self.simulation_toolbar.screenshot_action.triggered.connect(self._on_screenshot)
        self.simulation_toolbar.record_action.triggered.connect(self._on_record_toggle)

        # --- Export (screenshot / recording) ---
        self.export_manager = ExportManager(self, lambda: self.grid)

        # --- Initial grid ---
        self.grid = None

        # --- Simulation flags and data ---
        self.playing = False
        self.updated = False
        self.sim_file_path = None
        self.sim_time = None
        self.sim_data = None
        self.sim_settings = None
        self.current_time_index = 0

        # --- Timers ---
        # Key press delay timer (200 ms delay)
        self.key_press_timer = QTimer(self)
        self.key_press_timer.setSingleShot(True)
        self.key_press_timer.setInterval(animation_period)
        self.key_press_allowed = True

        def enable_key_press():
            self.key_press_allowed = True

        self.key_press_timer.timeout.connect(enable_key_press)

        # --- Key Press Event handler ---
        self.keyPressEvent = self.handle_key_press
        # TODO: fix focus issues with grid stealing keys

        # --- Load initial layout and data if provided ---
        # Programmatic path takes priority over file-based path.
        if grid is not None:
            self._load_grid_direct(grid)
            if sim_data is not None:
                self._load_sim_direct(sim_data, sim_settings if sim_settings is not None else {})
        else:
            if layout is not None:
                self.load_grid_layout(layout)
            if data_path is not None:
                self.load_csv(data_path)

    def handle_key_press(self, event):
        """Handle key press events."""
        key = event.key()

        if self.key_press_allowed:
            if key == Qt.Key_Space:  # Toggle play/pause
                if self.sim_data is not None:
                    self.play_simulation() if not self.playing else self.stop_simulation()

            elif key == Qt.Key_R:  # Reset simulation
                self.reset_simulation()

            elif key == Qt.Key_Left:  # Step backward
                step = self.get_slider_num_steps() // 100 * 5
                self.time_slider.setValue(max(0, self.time_slider.value() - step))
            elif key == Qt.Key_Right:  # Step forward
                step = self.get_slider_num_steps() // 100 * 5
                self.time_slider.setValue(
                    min(self.time_slider.maximum(), self.time_slider.value() + step)
                )

            elif key == Qt.Key_Comma:  # Step backward by 1
                self.time_slider.setValue(max(0, self.time_slider.value() - 1))
            elif key == Qt.Key_Period:  # Step forward by 1
                self.time_slider.setValue(
                    min(self.time_slider.maximum(), self.time_slider.value() + 1)
                )

            elif key == Qt.Key_Q:  # Quit application
                self.close()

            self.key_press_allowed = False
            self.key_press_timer.start()

    def get_slider_num_steps(self):
        """Return the current slider number of steps."""
        if self.time_slider is None:
            return 0
        return self.time_slider.maximum() - self.time_slider.minimum()

    def slider_pressed(self):
        self.stop_simulation()

    # ----------------------------------------------------------------------
    # GRID MANAGEMENT
    # ----------------------------------------------------------------------
    def clear_current_grid(self):
        """Safely remove and delete the existing grid widget."""
        if self.grid is not None:
            old_grid = self.grid
            self.setCentralWidget(None)  # Detach from the main window
            old_grid.deleteLater()  # Schedule for deletion
            self.grid = None

    def load_grid_layout(self, file_path: str) -> None:
        """Load a new grid layout from file, then reload any active CSV into it."""
        self.clear_current_grid()

        # Read layout info and set as central widget
        self.grid = load_grid_from_json(file_path)  # SimulationGrid
        self.setCentralWidget(self.grid)

        # Setup new scenes and timer
        self.grid.setup_scenes()
        self.grid.timer_set(self.next_simulation_step, step=self.animation_period)

        # Re-feed existing data into the new layout (error is shown to user on mismatch)
        if self.sim_file_path is not None:
            self.process_csv()

    def _load_grid_direct(self, grid: SimulationGrid) -> None:
        """Programmatic counterpart to :meth:`load_grid_layout`.

        Installs a pre-built :class:`~ssl_vista.ui.grid.SimulationGrid` as
        the central widget without reading any file from disk.

        Parameters
        ----------
        grid:
            A fully constructed :class:`~ssl_vista.ui.grid.SimulationGrid`
            (e.g. produced by :func:`~ssl_vista.ui.grid.load_grid_from_spec`).
        """
        self.clear_current_grid()
        self.grid = grid
        self.setCentralWidget(self.grid)
        self.grid.setup_scenes()
        self.grid.timer_set(self.next_simulation_step, step=self.animation_period)

    def _load_sim_direct(self, sim_data: SimData, sim_settings: SimSettings) -> None:
        """Programmatic counterpart to :meth:`process_csv`.

        Injects pre-parsed simulation data (the same structures that
        :func:`~ssl_simulator.utils.processing.load_sim` returns) without
        requiring a CSV file on disk.

        Parameters
        ----------
        sim_data:
            Simulation variable arrays keyed by field name.
            Must contain a ``"time"`` key with a sequence of timestamps.
        sim_settings:
            Scalar simulation parameters (``dt``, ``n_robots``, etc.).
        """
        if self.grid is None:
            return
        self.sim_data = sim_data
        self.sim_settings = sim_settings
        self.sim_time = self.sim_data["time"]
        self.time_slider.setRange(0, len(self.sim_time) - 1)
        self.time_slider.blockSignals(False)
        self.grid.reset_scenes(self.sim_data, self.sim_settings)
        self.reset_simulation()
        if self.auto_play:
            self.play_simulation()

    # ---------------------------------------------------------------
    # FILE LOADING METHODS
    # ---------------------------------------------------------------
    def load_csv(self, file_path):
        """Load simulation data from a CSV file."""
        if self.grid is None:
            QMessageBox.information(
                self, "Grid NOT Loaded", "Please load a grid layout before loading simulation data."
            )
            return
        if file_path:
            self.sim_file_path = file_path
            self.process_csv()

    def reload_csv(self):
        """Reload the currently loaded CSV file."""
        if self.sim_file_path is not None:
            self.process_csv()

    def process_csv(self):
        """Process the loaded CSV data, rolling back on incompatibility."""
        if self.sim_file_path is None:
            return

        # Snapshot current state so we can restore it if the new data is incompatible.
        prev_data = self.sim_data
        prev_settings = self.sim_settings
        prev_time = self.sim_time

        try:
            self.sim_data, self.sim_settings = load_sim(self.sim_file_path)
            self.sim_time = self.sim_data["time"]
            self.time_slider.setRange(0, len(self.sim_time) - 1)
            self.time_slider.blockSignals(False)
            self.grid.reset_scenes(self.sim_data, self.sim_settings)
            self.reset_simulation()
            if self.auto_play:
                self.play_simulation()
        except Exception as exc:
            # Roll back data state.
            self.sim_data = prev_data
            self.sim_settings = prev_settings
            self.sim_time = prev_time
            if prev_time is not None:
                self.time_slider.setRange(0, len(prev_time) - 1)
            _logger.error("CSV load failed: %s", exc)

            # Re-initialise plotters with the previous data so they are in a
            # consistent state — reset_scenes may have partially run before
            # failing, leaving some plotters cleared but not re-initialised.
            if prev_data is not None:
                try:
                    self.grid.reset_scenes(prev_data, prev_settings or {})
                    self.reset_simulation()
                except Exception:
                    # Rollback also failed — clear data so replay can't crash.
                    self.sim_data = None
                    self.sim_settings = None
                    self.sim_time = None

            QMessageBox.warning(
                self,
                "Incompatible Data",
                f"The selected file is not compatible with the current layout:\n\n{exc}",
            )

    # ---------------------------------------------------------------
    # SIMULATION CONTROL METHODS
    # ---------------------------------------------------------------
    def play_simulation(self):
        """Start playing the simulation."""
        if self.sim_data is None:
            return
        self.playing = True
        self.grid.timer_start()

    def stop_simulation(self):
        """Stop the simulation."""
        self.playing = False
        if self.grid is not None:
            self.grid.timer_stop()

    def reset_simulation(self):
        """Reset the simulation to the beginning."""
        self.updated = False
        self.time_slider.setValue(0)
        self.update_simulation()  # When time_slider value already 0

    def next_simulation_step(self, *args):
        """Advance the simulation by one time step."""
        if self.sim_data is None:
            return
        self.time_slider.setValue(min(self.time_slider.value() + 1, self.time_slider.maximum()))
        QApplication.processEvents()

    def update_time(self, value):
        """Update the simulation to the specified time index."""
        if self.sim_data is None:
            return
        if value != self.current_time_index:
            self.updated = False
        self.current_time_index = value
        time_step = self.sim_data["time"][self.current_time_index]
        self.time_label.setText(f"Time: {time_step:.2f} ")
        self.updated = self.update_simulation()

    def update_simulation(self):
        """Update the simulation visualization."""
        if self.sim_data is not None and not self.updated:
            if self.current_time_index < len(self.sim_time) - 1:
                self.grid.update_scenes(self.sim_data, self.current_time_index)
                self.updated = True
                self.export_manager.capture_frame()
            elif self.current_time_index == len(self.sim_time) - 1:
                self.grid.update_scenes(self.sim_data, self.current_time_index)
                self.export_manager.capture_frame()
                self.stop_simulation()
                self.updated = True
            else:
                _logger.error("Current time index exceeds simulation time range.")
        else:
            self.stop_simulation()

    # ---------------------------------------------------------------
    # EXPORT METHODS
    # ---------------------------------------------------------------
    def _on_screenshot(self):
        self.export_manager.take_screenshot()

    def _on_record_toggle(self):
        action = self.simulation_toolbar.record_action
        if self.export_manager.is_recording:
            self.export_manager.stop_recording()
            action.setIcon(make_icon("record"))
            action.setText("Record")
        else:
            default_fps = max(1, 1000 // self.animation_period)
            started = self.export_manager.start_recording(default_fps)
            if started:
                action.setIcon(make_icon("stop_rec"))
                action.setText("Stop Rec")

    def closeEvent(self, event):
        """Handle the close event to stop all timers and clean up."""
        if self.grid is not None:
            self.grid.timer_stop()
        self.key_press_timer.stop()
        event.accept()
