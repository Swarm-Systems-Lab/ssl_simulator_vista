"""Live-follow machinery: revision polling, the refresh lifecycle, and the window tick."""

import matplotlib

matplotlib.use("Agg")

import numpy as np

from ssl_vista.sources import LoggedSource, StreamSource


def _frame(k, n=2):
    return {"p": np.full((n, 3), float(k))}


# --------------------------------------------------------------------------- grid lifecycle
def test_grid_refresh_scenes_dispatches_to_every_plotter():
    from ssl_vista.ui.grid import SimulationGrid

    calls = []

    class P:
        def refresh_data(self, sim_data, sim_settings):
            calls.append((id(self), sim_settings))

    grid = SimulationGrid.__new__(SimulationGrid)
    grid._plotter_array = np.array([P(), None, P()], dtype=object).reshape(1, -1)
    grid.refresh_scenes({"time": np.zeros(1)}, {"g": 1})
    assert len(calls) == 2 and all(s == {"g": 1} for _, s in calls)


def test_mpl_refresh_data_refits_limits_as_data_grows():
    import matplotlib.pyplot as plt

    from ssl_vista.plotters.base_mpl import BaseMplPlotter

    plotter = BaseMplPlotter.__new__(BaseMplPlotter)
    plotter.artists, plotter.line_configs = {}, {}
    plotter.fig = plt.figure()
    plotter.axes = {"a": plotter.fig.add_subplot()}
    plotter.register_lines("a", "y", units="m")

    short = {"time": np.arange(3.0), "y": np.arange(3.0)}
    plotter._init_lines_from_config(short)
    assert plotter.axes["a"].get_xlim()[1] < 3.0 + 1e-9

    grown = {"time": np.arange(10.0), "y": np.arange(10.0) * 5}
    plotter.refresh_data(grown, {})
    assert plotter.axes["a"].get_xlim()[1] >= 9.0  # x followed the stream head
    assert plotter.axes["a"].get_ylim()[1] >= 45.0  # y followed the growing range


# --------------------------------------------------------------------------- window tick
class _Recorder:
    """Stub standing in for Qt widgets/grid: records calls, no Qt required."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args))

        return record

    def named(self, name):
        return [args for n, args in self.calls if n == name]


def _window(stream):
    from ssl_vista.backend import Session
    from ssl_vista.ui.main_window import MainWindow

    window = MainWindow.__new__(MainWindow)
    window.session = Session(stream)
    window.source = stream
    window.sim_data = stream
    window.sim_settings = stream.settings
    window.sim_time = None
    window.current_time_index = 0
    window.live_timer = _Recorder()
    window.time_slider = _Recorder()
    window.time_label = _Recorder()
    window.grid = _Recorder()
    window.export_manager = _Recorder()
    return window


def test_live_tick_defers_scene_init_until_frames_exist():
    stream = StreamSource()
    window = _window(stream)

    window._on_live_tick()  # empty stream: nothing to build yet
    assert window.session._scene_ready is False
    assert window.grid.named("reset_scenes") == []

    stream.push(0.0, _frame(0))
    window._on_live_tick()
    assert window.session._scene_ready is True
    assert len(window.grid.named("reset_scenes")) == 1  # first frames -> initial build
    assert len(window.grid.named("update_scenes")) == 1  # and rendered at the head


def test_live_tick_is_a_noop_when_nothing_changed_then_follows_growth():
    stream = StreamSource()
    stream.push(0.0, _frame(0))
    window = _window(stream)

    window._on_live_tick()
    n_updates = len(window.grid.named("update_scenes"))
    window._on_live_tick()  # same revision: no work
    assert len(window.grid.named("update_scenes")) == n_updates

    stream.push(0.1, _frame(1))
    window._on_live_tick()
    updates = window.grid.named("update_scenes")
    assert len(updates) == n_updates + 1
    assert updates[-1][1] == 1  # rendered at the new head
    assert len(window.grid.named("refresh_scenes")) == 1  # grown, not re-initialized


def test_detached_scrubbing_stops_following_the_head():
    stream = StreamSource()
    stream.push(0.0, _frame(0))
    window = _window(stream)
    window._on_live_tick()

    window.session.detach()  # what slider_pressed does
    stream.push(0.1, _frame(1))
    window._on_live_tick()

    # data-side refresh still happens, but the view is not dragged to the head
    assert len(window.grid.named("refresh_scenes")) == 1
    assert len(window.grid.named("update_scenes")) == 1  # only the initial one
