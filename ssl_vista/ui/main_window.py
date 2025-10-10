__all__ = ["MainWindow"]

import os
import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import Qt, QTimer

from ssl_vista import SimulationToolbar, load_grid_from_json, CONFIG
from ssl_simulator import load_sim

# For Wayland compatibility (e.g. Ubuntu)
os.environ['QT_QPA_PLATFORM'] = "xcb"

class MainWindow(QMainWindow):
    """Base simulation application with a toolbar and customizable grid layout."""
    def __init__(self, title="Simulation Viewer", 
                 layout=None, data_path=None, auto_play=False,
                 width_ratio=0.8, height_ratio=0.8, animation_period=40):
        super().__init__()
        self.setWindowTitle(title)
        self.auto_play = auto_play
        self.animation_period = animation_period # in ms

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

        # --- Initial grid ---
        self.grid = None

        # --- Simulation flags and data --- 
        self.playing = False
        self.updated = False
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

            elif key == Qt.Key_R: # Reset simulation
                self.reset_simulation()

            elif key == Qt.Key_Left:  # Step backward
                step = self.get_slider_num_steps() // 100 * 5
                self.time_slider.setValue(max(0, self.time_slider.value() - step))
            elif key == Qt.Key_Right:  # Step forward
                step = self.get_slider_num_steps() // 100 * 5
                self.time_slider.setValue(min(self.time_slider.maximum(), self.time_slider.value() + step))
            
            elif key == Qt.Key_Comma:  # Step backward by 1
                self.time_slider.setValue(max(0, self.time_slider.value() - 1))
            elif key == Qt.Key_Period:  # Step forward by 1
                self.time_slider.setValue(min(self.time_slider.maximum(), self.time_slider.value() + 1))
            
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
            old_grid.deleteLater()       # Schedule for deletion
            self.grid = None

    def load_grid_layout(self, file_path: str):
        """Load a new grid layout from file."""
        self.clear_current_grid()

        # Read layout info and set as central widget
        self.grid = load_grid_from_json(file_path) # SimulationGrid
        self.setCentralWidget(self.grid)

        # Setup new scenes and timer
        self.grid.setup_scenes()
        self.grid.timer_set(self.next_simulation_step, step=self.animation_period)

    # ---------------------------------------------------------------
    # FILE LOADING METHODS
    # ---------------------------------------------------------------
    def load_csv(self, file_path):
        """Load simulation data from a CSV file."""
        if self.grid is None:
            QMessageBox.information(self, "Grid NOT Loaded", "Please load a grid layout before loading simulation data.")
            return
        if file_path:
            self.sim_file_path = file_path
            self.process_csv()

    def reload_csv(self):
        """Reload the currently loaded CSV file."""
        if self.sim_file_path is not None:
            self.process_csv()
            
    def process_csv(self):
        """Process the loaded CSV data."""
        if self.sim_file_path is not None:
            self.sim_data, self.sim_settings = load_sim(self.sim_file_path, debug=CONFIG["DEBUG_INFO"])
            self.sim_time = self.sim_data['time']
            self.time_slider.setRange(0, len(self.sim_time) - 1)
            self.time_slider.blockSignals(False)
            self.grid.reset_scenes(self.sim_data, self.sim_settings)
            self.reset_simulation()
            if self.auto_play:
                self.play_simulation()

    # ---------------------------------------------------------------
    # SIMULATION CONTROL METHODS
    # ---------------------------------------------------------------
    def play_simulation(self):
        """Start playing the simulation."""
        self.playing = True
        self.grid.timer_start()
        # Placeholder for play logic

    def stop_simulation(self):
        """Stop the simulation."""
        self.playing = False
        self.grid.timer_stop()

    def reset_simulation(self):
        """Reset the simulation to the beginning."""
        self.updated = False
        self.time_slider.setValue(0)
        self.update_simulation()  # When time_slider value already 0

    def next_simulation_step(self, *args):
        """Advance the simulation by one time step."""
        self.time_slider.setValue(min(self.time_slider.value() + 1, self.time_slider.maximum()))
        QApplication.processEvents()

    def update_time(self, value):
        """Update the simulation to the specified time index."""
        if value != self.current_time_index:
            self.updated = False
        self.current_time_index = value
        time_step = self.sim_data['time'][self.current_time_index]
        self.time_label.setText(f"Time: {time_step:.2f}")
        self.updated = self.update_simulation()

    def update_simulation(self):
        """Update the simulation visualization."""
        if self.sim_data is not None and not self.updated:
            if self.current_time_index < len(self.sim_time)-1:
                self.grid.update_scenes(self.sim_data, self.current_time_index)
                self.updated = True
            elif self.current_time_index == len(self.sim_time) - 1:
                self.grid.update_scenes(self.sim_data, self.current_time_index)
                self.stop_simulation()
                self.updated = True
            else:       
                print("[ERROR] Time index out of bounds.")
        else:
            self.stop_simulation()
        
    def closeEvent(self, event):
        """Handle the close event to stop all timers and clean up."""
        if self.grid is not None:
            self.grid.timer_stop()
        self.key_press_timer.stop()
        event.accept()