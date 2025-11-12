import numpy as np
import matplotlib.pyplot as plt

from ssl_vista import BaseMplPlotter

from ssl_simulator.visualization import set_paper_parameters
set_paper_parameters(fontsize=24)

class PlotterMplExample(BaseMplPlotter):
    """
    Matplotlib plotter compatible with Qt layout.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.axes_config = {"main": {"position": [0.1,0.1,0.8,0.8]}}

    def init_artists(self, sim_data, sim_settings):
        self.artists = {}

        # Extract the first element in sim_data that is not "time"
        self.n_robots = next(value for key, value in sim_data.items() if key != "time").shape[1]

        ax = self.axes["main"]
        ax.clear()
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.grid(True)

        ax.set_xlim(sim_data["time"].min(), sim_data["time"].max())
        ax.set_ylim(sim_data["robot.theta"].min(), sim_data["robot.theta"].max())

        self.artists["lines"] = []
        for i in range(self.n_robots):
            line, = ax.plot([], [], color="royalblue", lw=2, label=f"Robot {i}")
            self.artists["lines"].append(line)

    def update_artists(self, sim_data, idx):
        """Wrapper called by FuncAnimation or manual update"""
        time = sim_data["time"]
        data_theta = sim_data["robot.theta"]

        for i, line in enumerate(self.artists["lines"]):
            line.set_data(time[:idx+1], data_theta[:idx+1, i])

        # self.axes["main"].relim()
        # self.axes["main"].autoscale_view()
        self.canvas.draw_idle()
