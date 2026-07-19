"""The Qt-free backend Session: poll decisions, follow state, commander handle."""

import numpy as np

from ssl_vista.backend import Session
from ssl_vista.sources import LoggedSource, StreamSource


def _stream(frames=0):
    stream = StreamSource()
    for k in range(frames):
        stream.push(k * 0.1, {"p": np.full((2, 3), float(k))})
    return stream


def test_poll_is_none_without_source_or_frames():
    assert Session().poll() is None
    assert Session(_stream(0)).poll() is None


def test_first_frames_trigger_scene_init_then_growth_refreshes():
    session = Session(_stream(1))
    first = session.poll()
    assert first.scene_init and not first.grew
    assert first.render_index == 0 and first.time == 0.0

    session.source.push(0.1, {"p": np.zeros((2, 3))})
    second = session.poll()
    assert second.grew and not second.scene_init
    assert second.render_index == 1

    assert session.poll() is None  # nothing changed since


def test_detach_keeps_data_flowing_but_stops_rendering_the_head():
    session = Session(_stream(1))
    session.poll()
    session.detach()
    session.source.push(0.1, {"p": np.zeros((2, 3))})
    update = session.poll()
    assert update is not None and update.grew
    assert update.render_index is None  # scrubbing: don't drag the view

    session.reattach()
    session.source.push(0.2, {"p": np.zeros((2, 3))})
    assert session.poll().render_index == 2


def test_rebinding_a_source_restarts_the_cursor():
    session = Session(_stream(2))
    session.poll()
    session.detach()

    session.set_source(_stream(3))
    assert session.follow is True  # fresh source, follow again
    update = session.poll()
    assert update.scene_init and update.render_index == 2


def test_is_live_reflects_the_source():
    assert Session(_stream(1)).is_live is True
    logged = LoggedSource({"time": np.zeros(1), "p": np.zeros((1, 2, 3))})
    assert Session(logged).is_live is False


def test_commander_rides_on_the_session():
    sent = []

    class FakeCommander:
        def setting(self, ac_id, index, value):
            sent.append((ac_id, index, value))

    session = Session(_stream(1), commander=FakeCommander())
    session.commander.setting(3, 1, 0.5)  # GCS panels talk to session.commander only
    assert sent == [(3, 1, 0.5)]
