# ssl_vista/config.py

import os


class Config(dict):
    def __setitem__(self, key, value):
        super().__setitem__(key, value)

    def update(self, *args, **kwargs):
        for _key, _value in dict(*args, **kwargs).items():
            pass
        super().update(*args, **kwargs)


# Initialize the configuration dictionary
CONFIG = Config(
    {
        "GRAPHICS": {
            # Default robot trajectory parameters
            "ROBOT_TRAJECTORY_SIZE": 4.0,
            "ROBOT_TRAJECTORY_OPACITY": 0.5,
            # Default size of the axes lines
            "AXES_LINE_WIDTH": 4.0,
            "AXES_LINE_LENGTH": 0.3,
            # Default size of the grid lines
            "GRID_LINE_WIDTH": 0.8,
        },
    }
)
