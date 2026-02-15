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
    "ssl_vista.plotters.pv_utils.scene_objects",
    "PyQt5",
]

REQUIRED_MODULES = BASIC_MODULES + GUI_MODULES


@pytest.mark.parametrize("module_name", BASIC_MODULES)
def test_import_module(module_name):
    """Test that required non-GUI modules can be imported."""
    importlib.import_module(module_name)


@pytest.mark.parametrize("module_name", GUI_MODULES)
@pytest.mark.skipif(
    not os.environ.get("DISPLAY") and os.environ.get("CI") == "true",
    reason="Skipping GUI tests in headless CI environment",
)
def test_import_gui_module(module_name):
    """Test that GUI modules can be imported (skipped in headless CI)."""
    importlib.import_module(module_name)


def test_python_version():
    """Test that the Python version is >= 3.8."""
    major, minor = sys.version_info[:2]
    assert (major, minor) >= (3, 8), f"Python 3.8+ required, found {major}.{minor}"


@pytest.mark.skipif(
    not os.environ.get("DISPLAY") and os.environ.get("CI") == "true",
    reason="Skipping GUI tests in headless CI environment",
)
def test_pyvista_qt_import():
    """Test that pyvistaqt can be imported and used."""
    import pyvistaqt

    assert hasattr(pyvistaqt, "BackgroundPlotter")


@pytest.mark.skipif(
    not os.environ.get("DISPLAY") and os.environ.get("CI") == "true",
    reason="Skipping GUI tests in headless CI environment",
)
def test_matplotlib_backend():
    """Test that matplotlib can use the Qt5Agg backend."""
    import matplotlib

    matplotlib.use("Qt5Agg", force=True)
    assert matplotlib.get_backend() == "Qt5Agg"
