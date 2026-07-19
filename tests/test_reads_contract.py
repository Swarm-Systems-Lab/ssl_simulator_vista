"""Plotters declare the components they consume, so a layout can be checked before rendering."""

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pytest

from ssl_vista.plotters._base_plotters import _BasePlotter
from ssl_vista.sources import LoggedSource, StreamSource


class _Fake(_BasePlotter):
    """Stands in for a real plotter: only the data contract matters here."""

    def __init__(self, reads=()):
        self._reads = tuple(reads)

    @property
    def reads(self):
        return self._reads


def _source(**arrays):
    arrays.setdefault("time", np.zeros(2))
    return LoggedSource(arrays)


def test_a_plotter_declares_nothing_by_default():
    assert _BasePlotter().reads == ()


def test_missing_components_against_a_source():
    plotter = _Fake(("p", "R"))
    assert plotter.missing_components(_source(p=np.zeros((2, 3, 3)))) == ["R"]
    assert plotter.missing_components(_source(p=np.zeros(2), R=np.zeros(2))) == []


def test_the_check_works_against_a_plain_dict_too():
    """Layouts predate the source protocol; a bare dict must still validate."""
    assert _Fake(("p",)).missing_components({"p": np.zeros(2)}) == []
    assert _Fake(("R",)).missing_components({"p": np.zeros(2)}) == ["R"]


def test_the_check_works_against_a_live_stream():
    stream = StreamSource()
    stream.push(0.0, {"p": np.zeros((2, 3))})
    assert _Fake(("p",)).missing_components(stream) == []
    assert _Fake(("p", "R")).missing_components(stream) == ["R"]


# --------------------------------------------------------------------------- grid wiring
def _grid(plotters):
    from ssl_vista.ui.grid import SimulationGrid

    grid = SimulationGrid.__new__(SimulationGrid)  # no Qt widgets needed for the check
    grid._plotter_array = np.array(plotters, dtype=object).reshape(1, -1)
    return grid


def test_grid_reports_which_plotter_lacks_what():
    grid = _grid([_Fake(("p",)), _Fake(("p", "R"))])
    report = grid.missing_components(_source(p=np.zeros(2)))
    assert list(report.values()) == [["R"]]
    assert "(0,1)" in next(iter(report))


def test_grid_raises_one_clear_error_naming_the_gap():
    grid = _grid([_Fake(("p", "theta"))])
    with pytest.raises(KeyError) as excinfo:
        grid.check_source(_source(p=np.zeros(2)))
    message = str(excinfo.value)
    assert "theta" in message and "Available" in message


def test_grid_accepts_a_source_that_satisfies_every_plotter():
    grid = _grid([_Fake(("p",)), _Fake(("p", "R"))])
    grid.check_source(_source(p=np.zeros(2), R=np.zeros(2)))  # must not raise


# --------------------------------------------------------------------------- real plotters
def test_the_mpl_plotter_derives_reads_from_its_registered_lines():
    from ssl_vista.plotters.base_mpl import BaseMplPlotter

    plotter = BaseMplPlotter.__new__(BaseMplPlotter)
    plotter.line_configs = {
        "a": {"var": "objective"},
        "b": {"var": "phi"},
        "c": {"var": "phi"},  # duplicates collapse
    }
    assert plotter.reads == ("objective", "phi")
