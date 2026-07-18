# ssl_vista/config.py


class Config(dict):
    """A plain dict for global runtime flags.

    Graphics/style defaults now live in typed models - see
    :mod:`ssl_vista.plotters.pv_utils.configs` (``GraphicsConfig``, ``GridConfig``, ...).
    """


# Global runtime flags (currently empty; reserved for non-style runtime toggles).
CONFIG = Config()
