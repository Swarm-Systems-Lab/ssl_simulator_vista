# ssl_vista/config.py

import os

class Config(dict):
    def __setitem__(self, key, value):
        print(f"SSL vista configuration updated: {key} = {value}")
        super().__setitem__(key, value)

    def update(self, *args, **kwargs):
        for key, value in dict(*args, **kwargs).items():
            print(f"SSL vista configuration updated: {key} = {value}")
        super().update(*args, **kwargs)

# Initialize the configuration dictionary
CONFIG = Config({
    "DEBUG":      False,
    "DEBUG_INFO": False,
    "WARNINGS":   True,
    "GRAPHICS": {
        # Default robot trajectory parameters
        "ROBOT_TRAJECTORY_SIZE": 5.0,
        "ROBOT_TRAJECTORY_OPACITY": 0.6,
        # Default size of the axes lines
        "AXES_LINE_WIDTH": 6.0,
        # Default size of the grid lines
        "GRID_LINE_WIDTH": 0.8,
    },
})
