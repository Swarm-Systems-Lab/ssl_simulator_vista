__all__ = ["_BasePlotter", "_BaseVisualPlotter"]

import logging

import numpy as np
import pyvista as pv
from PyQt5 import QtCore, QtGui
from pyvistaqt import QtInteractor

from .pv_utils.debug import _actor_snapshot
from .pv_utils.scene_objects import SceneObject, SceneObjectBundle

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
    # ABSTRACT METHODS (must be implemented)
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

        # - Dictionary storing all scene objects
        self.scene_objects = {}  # dict of SceneObject

        # - Connect to context signals
        self.context.robot_focus_changed.connect(self._robot_focus_changed)

    # ---------------------------------------------------------------
    # ABSTRACT METHODS (must be implemented)
    # ---------------------------------------------------------------
    def setup_scene(self):
        """Set up the initial scene (camera, actors, grid, etc)."""
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
    def add_scene_object(self, bundle_name: str, bundle: SceneObject | SceneObjectBundle):
        """
        Add a SceneObject or all children from a SceneObjectBundle to the scene.

        If a SceneObjectBundle is provided, each child will be registered with the name:
        "{bundle_name}.{child_name}". If a single SceneObject is provided, it will be
        registered directly under the given bundle_name.

        Parameters
        ----------
        bundle_name : str
            Name or prefix for the object(s) being added.
        bundle : SceneObject or SceneObjectBundle
            The object or bundle containing multiple scene objects or nested bundles.

        Returns
        -------
        bundle : SceneObject or SceneObjectBundle
            The same object or bundle (for chaining).

        Example
        -------
        # Adding a single SceneObject
        sphere = SceneObject(mesh=sphere_mesh)
        self.add_scene_object("sphere", sphere)

        # Adding a SceneObjectBundle
        sphere_bundle = SphereGrid(radius=1.0)
        self.add_scene_object("sphere_grid", sphere_bundle)
        """
        if isinstance(bundle, SceneObject):
            style = bundle.style.copy()

            # Extract "visible" if present in style
            visible = style.pop("visible", True)
            bundle.set_visibility(visible)

            # Add a single SceneObject
            actor = self.pvqt.add_mesh(bundle.mesh, **style)
            bundle.actor = actor
            actor.visibility = visible
            self.scene_objects[bundle_name] = bundle

        elif isinstance(bundle, SceneObjectBundle):
            # Add all children from a SceneObjectBundle
            for child_name, child_data in bundle.children.items():
                obj = child_data["obj"]
                style = child_data["style"]
                full_name = f"{bundle_name}.{child_name}"

                # Check if the object is another SceneObjectBundle
                if isinstance(obj, SceneObjectBundle):
                    self.add_scene_object(full_name, obj)
                else:
                    # Extract "visible" if present in style
                    visible = style.pop("visible", True)
                    obj.set_visibility(visible)

                    # Add the child object with its styling
                    actor = self.pvqt.add_mesh(obj.mesh, **style)
                    actor.visibility = visible
                    obj.actor = actor
                    self.scene_objects[full_name] = obj
        else:
            raise TypeError("The 'bundle' parameter must be a SceneObject or SceneObjectBundle.")

        return bundle

    def remove_scene_object(self, name: str):
        """Remove a scene object from the plotter."""
        if name in self.scene_objects:
            actor = self.scene_objects[name].actor
            self.pvqt.remove_actor(actor)
            del self.scene_objects[name]

    def remove_scene_object_bundle(self, bundle_name: str):
        """
        Remove all scene objects that belong to a bundle.

        Parameters
        ----------
        bundle_name : str
            The prefix used when adding the bundle
        """
        # Find all objects with this prefix
        keys_to_remove = [k for k in self.scene_objects if k.startswith(f"{bundle_name}_")]
        for key in keys_to_remove:
            self.remove_scene_object(key)

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

        Pure data — no logging side effects. The caller decides whether and
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
