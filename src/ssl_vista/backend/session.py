"""The viewer/GCS backend, Qt-free: one object owning source, cursor, and commander.

``Session`` is what every frontend (the Qt MainWindow, a future QML GCS, a notebook, a headless
recorder) programs against:

- **telemetry in**: a bound :class:`~ssl_tmtc.sources.DataSource` (log, running sim, UDP, Ivy);
- **cursor**: the follow-live / scrub state machine, with the change-detection logic that used to
  live inside the Qt window's timer callback;
- **command out**: an optional :class:`~ssl_tmtc.command.Commander`, so GCS panels call
  ``session.commander.setting(...)`` and never touch a transport.

Frontends drive it with a periodic :meth:`poll` (Qt: a QTimer; scripts: a loop) and apply the
returned :class:`SessionUpdate` to their widgets. Polling keeps sources and this backend free of
any UI framework and makes threading trivial -- producers push from anywhere, only the frontend
thread renders.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Session", "SessionUpdate"]


@dataclass(frozen=True)
class SessionUpdate:
    """What changed since the previous poll -- everything a frontend needs to apply."""

    n_frames: int
    scene_init: bool  # first frames arrived: (re)build scenes
    grew: bool  # data extended: refresh run-derived state (limits, caches)
    render_index: int | None  # frame to draw now (following), or None (detached)
    time: float | None  # timestamp of render_index, when rendering


class Session:
    def __init__(self, source=None, commander=None):
        self.source = None
        self.commander = commander
        self.follow = True
        self._revision = -1
        self._scene_ready = False
        if source is not None:
            self.set_source(source)

    # -- source binding ---------------------------------------------------------------------------
    def set_source(self, source) -> None:
        """Bind a new data source; the cursor and scene state start over."""
        self.source = source
        self.follow = True
        self._revision = -1
        self._scene_ready = False

    @property
    def is_live(self) -> bool:
        return self.source is not None and getattr(self.source, "is_live", False)

    # -- cursor -----------------------------------------------------------------------------------
    def detach(self) -> None:
        """Stop chasing the stream head (the user grabbed the slider)."""
        self.follow = False

    def reattach(self) -> None:
        """Follow the head again (the user pressed Play on a live source)."""
        self.follow = True

    # -- the poll ---------------------------------------------------------------------------------
    def poll(self) -> SessionUpdate | None:
        """Change detection + cursor decision. ``None`` means: nothing to do this tick.

        The exact logic the live QTimer callback used to hold: revision-based change detection
        (survives ring wrap, where the frame *count* saturates but content advances), deferred
        scene init until the first frame exists, and head-rendering only while following.
        """
        source = self.source
        if source is None:
            return None
        revision = getattr(source, "revision", source.n_frames)
        if revision == self._revision:
            return None
        self._revision = revision

        n_frames = source.n_frames
        if n_frames == 0:
            return None

        scene_init = not self._scene_ready
        self._scene_ready = True

        head = n_frames - 1
        render = head if self.follow else None
        return SessionUpdate(
            n_frames=n_frames,
            scene_init=scene_init,
            grew=not scene_init,
            render_index=render,
            time=source.time(head) if render is not None else None,
        )
