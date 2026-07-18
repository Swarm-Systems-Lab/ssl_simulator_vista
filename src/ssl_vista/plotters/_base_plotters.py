__all__ = ["_BasePlotter", "_BaseVisualPlotter"]

import logging

import numpy as np
import pyvista as pv
from PyQt5 import QtCore, QtGui
from pyvistaqt import QtInteractor

from .pv_utils.debug import _actor_snapshot
from .pv_utils.scene import Drawable, SceneObject

_logger = logging.getLogger(__name__)


class _BasePlotter:
    def __init__(self, **kwargs):
        self.widget = None

    def set_widget(self, widget):
        """Set the Qt widget for layouts."""
        self.widget = widget
        try:
            # TODO: Set event handlers during initialization
            self.widget.keyPressEvent = self.keyPressEvent
            self.widget.keyReleaseEvent = self.keyReleaseEvent
            self.widget.setFocusPolicy(QtCore.Qt.ClickFocus)
            self.widget.setFocus()
        except AttributeError:
            _logger.warning(
                f"Unable to set key event handlers on widget of type {type(self.widget).__name__}"
            )

    def get_widget(self):
        """Return the Qt widget for layouts."""
        return self.widget

    # ---------------------------------------------------------------
    # DATA CONTRACT
    # ---------------------------------------------------------------
    @property
    def reads(self) -> tuple[str, ...]:
        """Component names this plotter needs from the data source.

        The analogue of ``ssl_simulator.System.reads``: declaring the dependency lets a layout be
        checked against a source *before* rendering, instead of failing with a ``KeyError`` partway
        through an animation. It is a property rather than a class attribute because most plotters
        resolve their component names at construction (configurable labels, registered lines).

        Return ``()`` to opt out of checking.
        """
        return ()

    def missing_components(self, source) -> list[str]:
        """Which of :attr:`reads` the given source cannot provide."""
        available = getattr(source, "components", None) or set(source)
        return [name for name in self.reads if name not in available]

    # ---------------------------------------------------------------
    # AUTHORING CONTRACT (implemented by every plotter, any backend)
    # ---------------------------------------------------------------
    # Leaf plotters implement `init_artists` / `update_artists`; the framework
    # lifecycle methods below (`setup_scene` / `reset_scene` /
    # `update_all_scene_objects`) are what the grid driver calls and are wired to
    # them by each backend base class (PyVista, Matplotlib, and future pyqtgraph).
    def init_artists(self, sim_data, sim_settings):
        """Create the scene's artists from data. Implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement init_artists()")

    def update_artists(self, sim_data, idx):
        """Update the scene's artists for frame ``idx``. Implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement update_artists()")

    # ---------------------------------------------------------------
    # FRAMEWORK LIFECYCLE (called by the grid driver)
    # ---------------------------------------------------------------
    def setup_scene(self):
        """Set up the initial scene"""
        raise NotImplementedError("Subclasses must implement setup_scene()")

    def reset_scene(self, sim_data, sim_settings):
        """Reset the scene to its initial state."""
        raise NotImplementedError("Subclasses must implement reset_scene()")

    def update_all_scene_objects(self, sim_data, idx):
        """
        Update all objects in the scene.
        Subclasses must implement this to update positions, orientations, etc.
        """
        raise NotImplementedError("Subclasses must implement update_all_scene_objects()")

    def reset_view(self) -> None:
        """Restore the initial camera / view state. No-op by default."""

    # ---------------------------------------------------------------
    # KEY EVENT HANDLING (can be overridden)
    # ---------------------------------------------------------------
    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """Shadow all key presses to avoid default widget behavior."""
        # print(f"{type(self.widget).__name__} - key pressed:", event.key())
        event.accept()  # prevent further processing

    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        """Shadow all key releases to avoid default widget behavior."""
        event.accept()

    # ---------------------------------------------------------------
    # DIAGNOSTICS (can be overridden)
    # ---------------------------------------------------------------
    def collect_scene_objects(self, verbose: bool = False) -> dict:
        """Return a structured snapshot of this plotter's contents.

        Default implementation returns just the class name. Subclasses with
        actual scene contents (PyVista actors, matplotlib artists, etc.)
        should override to include them.
        """
        return {"plotter": self.__class__.__name__}


class _BaseVisualPlotter(_BasePlotter):
    """
    Base class for a PyVista QtInteractor Plotter.

    Subclasses MUST implement:
      - setup_scene(): initialize actors, camera, grid, etc.
      - reset_scene(): reset the scene to initial state
      - update_all_scene_objects(*args, **kwargs): update positions, orientations, etc.
    """

    def __init__(self, parent=None, context=None, widget=None, **kwargs):
        super().__init__(**kwargs)
        self.context = context
        self.pvqt = QtInteractor(parent=parent)
        self.set_widget(self.pvqt)

        # - Registries: flat leaf actors, plus top-name -> leaf-names for groups.
        self.scene_objects = {}  # full_name -> SceneObject (leaf)
        self._scene_groups = {}  # top_name -> [full leaf names]

        # - Connect to context signals
        self.context.robot_focus_changed.connect(self._robot_focus_changed)

    # ---------------------------------------------------------------
    # FRAMEWORK LIFECYCLE (wired to init_artists / update_artists)
    # ---------------------------------------------------------------
    def setup_scene(self):
        """Set up the initial scene (camera, lights, grid). Implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement setup_scene()")

    def reset_scene(self, sim_data, sim_settings):
        """Clear existing artists and (re)build them from data via init_artists()."""
        self.clear_scene_objects()
        self.init_artists(sim_data, sim_settings)
        self.pvqt.reset_camera()

    def update_all_scene_objects(self, sim_data, idx):
        """Update artists for frame ``idx`` via update_artists(), then render."""
        self.update_artists(sim_data, idx)
        self.pvqt.render()

    # ---------------------------------------------------------------
    # ABSTRACT CONTEXT SIGNALS CALLBACKS (can be overridden)
    # ---------------------------------------------------------------
    def when_change_robot_focus(self, idx_new_focus, idx_prv_focus):
        """Handle robot focus change. Can be overridden by subclasses."""
        pass

    # ---------------------------------------------------------------
    # PYVISTA QTINTERACTOR SHORTHCUTS
    # ---------------------------------------------------------------
    def reset_camera(self):
        return self.pvqt.reset_camera()

    # ---------------------------------------------------------------
    # SCENE OBJECT MANAGEMENT
    # ---------------------------------------------------------------
    def add_scene_object(self, name: str, obj: Drawable):
        """Add any :class:`Drawable` to the scene.

        The drawable creates its own actor(s) via ``obj._attach(pvqt, name)`` and
        returns its leaf objects. A single :class:`SceneObject` registers under
        ``name``; a :class:`SceneObjectGroup` registers each leaf as
        ``"{name}.{child_name}"``. Any object implementing the ``_attach`` protocol
        (including user-defined ones) integrates without special-casing.

        Returns the same object for chaining.

        Example
        -------
        sphere = Mesh(pv.Sphere(), color="orange")
        self.add_scene_object("sphere", sphere)
        sphere.set_pose(position=[1, 0, 0])
        """
        if not isinstance(obj, Drawable):
            raise TypeError("add_scene_object expects a Drawable (SceneObject / SceneObjectGroup).")

        leaves = obj._attach(self.pvqt, name)
        self._scene_groups[name] = [full_name for full_name, _leaf in leaves]
        for full_name, leaf in leaves:
            self.scene_objects[full_name] = leaf
        return obj

    def remove_scene_object(self, name: str):
        """Remove a scene object (single leaf or a whole group added under ``name``)."""
        full_names = self._scene_groups.pop(name, None)
        if full_names is None:
            full_names = [name] if name in self.scene_objects else []
        for full_name in full_names:
            leaf = self.scene_objects.pop(full_name, None)
            if leaf is not None and leaf.actor is not None:
                self.pvqt.remove_actor(leaf.actor)

    def clear_scene_objects(self):
        """Remove every scene object's actor and reset the registries."""
        for leaf in self.scene_objects.values():
            if leaf.actor is not None:
                self.pvqt.remove_actor(leaf.actor)
        self.scene_objects.clear()
        self._scene_groups.clear()

    # ---------------------------------------------------------------
    # CONTEXT SIGNALS CALLBACKS
    # ---------------------------------------------------------------
    def _robot_focus_changed(self):
        idx_prv_focus = self.context.prev_robot_focus
        idx_new_focus = self.context.robot_focus
        self.when_change_robot_focus(idx_new_focus, idx_prv_focus)

    # ---------------------------------------------------------------
    # DIAGNOSTICS
    # ---------------------------------------------------------------
    def collect_scene_objects(self, verbose: bool = False) -> dict:
        """Return a structured snapshot of this plotter's scene objects.

        Pure data - no logging side effects. The caller decides whether and
        how to log it.
        """
        objects = {}
        for name, obj in self.scene_objects.items():
            entry = {
                "mesh": type(obj.mesh).__name__,
                "actor": type(obj.actor).__name__,
            }
            if verbose:
                entry["snapshot"] = _actor_snapshot(obj.actor)
            objects[name] = entry

        return {
            "plotter": self.__class__.__name__,
            "objects": objects,
        }
