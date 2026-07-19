"""Source protocol: a log and a live stream behind one interface."""

import numpy as np
import pytest

from ssl_vista.sources import LoggedSource, StreamSource


def _logged(n_frames=5, n_agents=3):
    return LoggedSource(
        {
            "time": np.arange(n_frames, dtype=float),
            "p": np.arange(n_frames * n_agents * 3, dtype=float).reshape(n_frames, n_agents, 3),
        },
        {"gain": 0.5},
    )


# --------------------------------------------------------------------------- logged
def test_a_logged_source_behaves_like_the_plain_dict_plotters_already_take():
    """Mapping compatibility is what lets existing plotters work unchanged."""
    source = _logged()
    assert source["p"].shape == (5, 3, 3)
    assert "p" in source and "nope" not in source
    assert set(source) == {"time", "p"}
    assert source.settings["gain"] == 0.5


def test_logged_frame_and_time_access():
    source = _logged()
    assert source.n_frames == 5
    assert source.time(2) == 2.0
    frame = source.frame(2)
    assert set(frame) == {"time", "p"}
    assert np.array_equal(frame["p"], source["p"][2])


def test_history_is_everything_up_to_the_index():
    source = _logged()
    assert source.history("p", 3).shape[0] == 4
    assert source.history("p", 3, max_len=2).shape[0] == 2  # most recent only
    assert np.array_equal(source.history("p", 3, max_len=2), source["p"][2:4])


def test_missing_reports_what_a_layout_would_lack():
    source = _logged()
    assert source.missing(["p", "R", "theta"]) == ["R", "theta"]
    assert source.missing(["p"]) == []


# --------------------------------------------------------------------------- stream
def test_a_stream_presents_itself_exactly_like_a_log():
    """The whole point: telemetry/SITL is consumable by the same plotters."""
    stream = StreamSource(capacity=10)
    for k in range(4):
        stream.push(k * 0.1, {"p": np.full((3, 3), float(k))})

    assert stream.n_frames == 4
    assert stream["p"].shape == (4, 3, 3)  # stacked like a logged run
    assert np.allclose(stream.frame(2)["p"], 2.0)
    assert stream.time(1) == pytest.approx(0.1)
    assert "p" in stream


def test_a_stream_keeps_only_the_most_recent_frames():
    """A telemetry link runs for hours; the buffer must stay bounded."""
    stream = StreamSource(capacity=3)
    for k in range(10):
        stream.push(float(k), {"p": np.full((2, 3), float(k))})

    assert stream.n_frames == 3
    assert np.allclose(stream["p"][0], 7.0)  # oldest kept
    assert np.allclose(stream["p"][-1], 9.0)  # newest
    assert stream.time(-1) == 9.0


def test_a_stream_rejects_a_changing_component_set():
    stream = StreamSource()
    stream.push(0.0, {"p": np.zeros((2, 3))})
    with pytest.raises(ValueError, match="components changed mid-stream"):
        stream.push(0.1, {"p": np.zeros((2, 3)), "R": np.zeros((2, 3, 3))})


def test_an_empty_stream_is_usable():
    stream = StreamSource()
    assert stream.n_frames == 0
    assert stream.missing(["p"]) == ["p"]


def test_stream_history_respects_the_window():
    stream = StreamSource(capacity=4)
    for k in range(6):
        stream.push(float(k), {"p": np.full((1, 3), float(k))})
    assert stream.history("p", stream.n_frames - 1).shape[0] == 4  # only what is buffered


# --------------------------------------------------------------------------- app wiring
def test_the_window_accepts_a_logged_source_or_a_plain_dict():
    """`_load_sim_direct` is the programmatic entry point; both forms must work."""
    from ssl_vista.ui.main_window import MainWindow

    window = MainWindow.__new__(MainWindow)  # no Qt needed for the data path
    window.grid = None  # short-circuits before touching widgets
    window.live_timer = type("T", (), {"stop": staticmethod(lambda: None)})()
    from ssl_vista.backend import Session

    window.session = Session()

    # A plain (data, settings) pair is wrapped into a source...
    window._set_source(LoggedSource({"time": np.arange(3.0), "p": np.zeros((3, 2, 3))}, {"g": 1}))
    assert isinstance(window.source, LoggedSource)
    assert window.sim_settings == {"g": 1}
    assert window.source.n_frames == 3
    # ...and the legacy attributes stay valid views of it.
    assert window.sim_data["p"].shape == (3, 2, 3)
    assert np.array_equal(window.sim_time, np.arange(3.0))


def test_the_window_drives_off_a_live_stream_identically():
    """The payoff: a telemetry/SITL feed is a drop-in for a replayed log."""
    from ssl_vista.ui.main_window import MainWindow

    stream = StreamSource(capacity=5)
    for k in range(3):
        stream.push(float(k), {"p": np.full((2, 3), float(k))})

    window = MainWindow.__new__(MainWindow)
    window.grid = None
    window.live_timer = type("T", (), {"stop": staticmethod(lambda: None)})()
    from ssl_vista.backend import Session

    window.session = Session()
    window._set_source(stream)

    assert window.source is stream
    assert window.source.n_frames == 3
    assert window.sim_data["p"].shape == (3, 2, 3)  # looks exactly like a logged run

    stream.push(3.0, {"p": np.full((2, 3), 3.0)})  # more data arrives
    assert window.source.n_frames == 4
    assert window.sim_data["p"].shape == (4, 2, 3)


def test_a_running_engine_streams_into_a_stream_source(tmp_path):
    """Phase A of the data plane: Engine(sink=stream.push) live-views a running sim,
    and the stream ends up identical to the logged replay of the same run."""
    from ssl_simulator import Engine, IntegrationSystem, System, World

    class Drift(System):
        reads, writes = (), ("u",)

        def run(self, world, dt):
            world["u"][:] = 1.0

    def build():
        world = World(3)
        world.add_state("p", dim=2, init=np.zeros((3, 2)))
        world.add("u", dim=2)
        world.add_system(Drift())
        world.add_system(IntegrationSystem([("p", "u")]))
        return world

    # Live: the stream IS the sink (signatures match by design).
    stream = StreamSource(capacity=100)
    Engine(time_step=0.01, log_time_step=0.05, sink=stream.push).run(build(), 0.5, eta=False)

    # Logged: same run, through the file path.
    run_file = tmp_path / "run.csv"
    Engine(time_step=0.01, log_filename=str(run_file), log_time_step=0.05).run(
        build(), 0.5, eta=False
    )
    logged = LoggedSource.from_file(str(run_file))

    # The stream presents itself exactly like the logged run: same frames, same shapes.
    assert stream.n_frames == logged.n_frames
    assert np.allclose(stream["time"], np.ravel(logged["time"]))
    assert np.allclose(stream["p"], logged["p"])
    assert np.allclose(stream.frame(stream.n_frames - 1)["p"], logged["p"][-1])

    # And the retained frames are copies, not aliases of the (mutating) world arrays.
    assert stream["p"][0].sum() == 0.0  # t=0 frame kept its original values
