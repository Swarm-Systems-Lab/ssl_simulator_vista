"""
Basic environment and compatibility tests for ssl_vista project.
"""

import importlib
import os
import sys

import pytest

# Non-GUI modules that can be imported in headless environments
BASIC_MODULES = [
    "ssl_vista",
    "ssl_vista.config",
    "ssl_vista.data",
    "pyvista",
    "matplotlib",
    "ipywidgets",
]

# GUI modules that require display/OpenGL
GUI_MODULES = [
    "ssl_vista.plotters",
    "ssl_vista.plotters.pv_utils.scene",
    "PyQt5",
]

REQUIRED_MODULES = BASIC_MODULES + GUI_MODULES

# A Qt/OpenGL display is needed to actually *use* the GUI stack (importing the
# bindings is fine, but loading an interactive backend is not). Treat the run as
# headless when neither an X11 nor a Wayland display is advertised - this covers
# local headless shells as well as CI, so it no longer keys off the CI env var.
_HEADLESS = not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
_requires_display = pytest.mark.skipif(
    _HEADLESS, reason="no display available (headless environment)"
)


@pytest.mark.parametrize("module_name", BASIC_MODULES)
def test_import_module(module_name):
    """Test that required non-GUI modules can be imported."""
    importlib.import_module(module_name)


@pytest.mark.parametrize("module_name", GUI_MODULES)
@_requires_display
def test_import_gui_module(module_name):
    """Test that GUI modules can be imported (skipped in headless environments)."""
    importlib.import_module(module_name)


def test_python_version():
    """Test that the Python version is >= 3.8."""
    major, minor = sys.version_info[:2]
    assert (major, minor) >= (3, 8), f"Python 3.8+ required, found {major}.{minor}"


@_requires_display
def test_pyvista_qt_import():
    """Test that pyvistaqt can be imported and used."""
    import pyvistaqt

    assert hasattr(pyvistaqt, "BackgroundPlotter")


@_requires_display
def test_matplotlib_backend():
    """Test that matplotlib can use the Qt5Agg backend."""
    import matplotlib

    matplotlib.use("Qt5Agg", force=True)
    assert matplotlib.get_backend() == "Qt5Agg"
