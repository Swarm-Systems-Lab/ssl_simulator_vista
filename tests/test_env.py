"""
Basic environment and compatibility tests for ssl_vista project.
"""

import importlib
import sys

import pytest

REQUIRED_MODULES = [
    "ssl_vista",
    "ssl_vista.config",
    "ssl_vista.data",
    "ssl_vista.plotters",
    "ssl_vista.plotters.pv_utils.scene_objects",
    "pyvista",
    "matplotlib",
    "ipywidgets",
    "PyQt5",
]


@pytest.mark.parametrize("module_name", REQUIRED_MODULES)
def test_import_module(module_name):
    """Test that required modules can be imported."""
    importlib.import_module(module_name)


def test_python_version():
    """Test that the Python version is >= 3.8."""
    major, minor = sys.version_info[:2]
    assert (major, minor) >= (3, 8), f"Python 3.8+ required, found {major}.{minor}"


def test_pyvista_qt_import():
    """Test that pyvistaqt can be imported and used."""
    import pyvistaqt

    assert hasattr(pyvistaqt, "BackgroundPlotter")


def test_matplotlib_backend():
    """Test that matplotlib can use the Qt5Agg backend."""
    import matplotlib

    matplotlib.use("Qt5Agg", force=True)
    assert matplotlib.get_backend() == "Qt5Agg"
