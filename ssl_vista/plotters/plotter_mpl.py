__all__ = ["PlotterMatplotlib"]

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from ssl_simulator.visualization import PlotBase


class PlotterMatplotlib(PlotBase):
    """
    Matplotlib plotter compatible with Qt layout.
    """

    def __init__(self, parent=None, figsize=(5,4), dpi=100):
        super().__init__(figsize=figsize, dpi=dpi)
        self.parent = parent
        self.axes_config = {"main": {"position": [0.1,0.1,0.8,0.8]}}
        self.positions = None  # will hold (n_frames, n_robots, 2)
        self.n_frames = 0

        # Embed in Qt if parent provided
        self.canvas = FigureCanvas(self.fig)
        if parent:
            self.canvas.setParent(parent)

    def get_widget(self):
        """Return the Qt widget for layouts."""
        return self.canvas

    def init_artists(self):
        self.setup_axes()
        self.artists = {}
        self.artists_list = []

        ax = self.axes["main"]
        ax.clear()
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        self.artists["lines"] = []
        for i in range(self.n_robots):
            line, = ax.plot([], [], color=self.robot_colors[i], lw=2, label=f"Robot {i}")
            self.artists["lines"].append(line)
        ax.legend()

        # Prepare for blitting/updates
        self.artists_list = self.artists["lines"]

    def update_artists(self, frame_data):
        """
        frame_data: array of shape (n_robots, 2)
        """
        for i, line in enumerate(self.artists["lines"]):
            x, y = frame_data[i, 0], frame_data[i, 1]
            old_x = line.get_xdata().tolist()
            old_y = line.get_ydata().tolist()
            line.set_data(old_x + [x], old_y + [y])

        self.axes["main"].relim()
        self.axes["main"].autoscale_view()
        self.canvas.draw_idle()

    def update(self, frame_idx):
        """Wrapper called by FuncAnimation or manual update"""
        frame_data = self.positions[frame_idx]
        self.update_artists(frame_data)
        return self.artists_list
