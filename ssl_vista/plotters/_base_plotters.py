__all__ = [
    "BasePlotter",
    "BaseVisualPlotter"
    ]

import os

import numpy as np
from pyvistaqt import QtInteractor
from PyQt5 import  QtCore, QtGui

from ssl_vista import CONFIG
from .pv_utils import inspect_actor

class BasePlotter:
    def set_widget(self, widget):
        """Set the Qt widget for layouts."""
        self.widget = widget

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


class BaseVisualPlotter(BasePlotter, QtInteractor):
    """
    Base class for a PyVista QtInteractor canvas.
    
    Subclasses MUST implement:
      - setup_scene(): initialize actors, camera, grid, etc.
      - reset_scene(): reset the scene to initial state
      - update_all_scene_objects(*args, **kwargs): update positions, orientations, etc.
    """

    def __init__(self, parent=None, context=None, **kwargs):
        super().__init__(parent=parent, **kwargs)
        self.context = context
        self.widget = self

        # Dictionary storing all scene objects
        # Format: "object_name": {"mesh": mesh, "actor": actor}
        self.scene_objects = {}

        # # Ensure proper focus so toolbars get keyboard input
        # self.setFocusPolicy(QtCore.Qt.StrongFocus)
    
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
    # KEY EVENT HANDLING
    # ---------------------------------------------------------------
    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """Shadow all key presses to avoid default VTK behavior."""
        key = event.key()
        if key == QtCore.Qt.Key_R:
            self.reset_camera()
        event.accept()  # Stop propagation to PyVista/VTK

    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        """Shadow all key releases."""
        event.accept()

    # ---------------------------------------------------------------
    # SCENE OBJECT MANAGEMENT
    # ---------------------------------------------------------------
    def add_scene_object(self, name: str, mesh, visible=True, **kwargs):
        """
        Add a mesh to the scene and store it.
        
        Parameters
        ----------
        name : str
            Unique name for the object.
        mesh : pyvista.DataSet
            The mesh to add.
        kwargs : dict
            Additional arguments passed to `add_mesh`.
        
        Returns
        -------
        mesh
        """
        if name in self.scene_objects:
            raise ValueError(f"Scene object '{name}' already exists.")

        # Temporarily disable rendering
        actor = self.add_mesh(mesh, **kwargs)
        actor.visibility = visible
        self.scene_objects[name] = {"mesh": mesh, "actor": actor}
        return mesh

    def remove_scene_object(self, name: str):
        """Remove a scene object from the plotter."""
        if name in self.scene_objects:
            actor = self.scene_objects[name]["actor"]
            self.remove_actor(actor)
            del self.scene_objects[name]

    def get_all_object_meshes(self):
        """Return a list of all mesh objects in the scene."""
        return [v["mesh"] for v in self.scene_objects.values()]

    def get_actor(self, name: str):
        """Return the VTK actor of a scene object."""
        return self.scene_objects[name]["actor"] if name in self.scene_objects else None

    # ---------------------------------------------------------------
    # SCENE MANAGEMENT
    # ---------------------------------------------------------------
    def camera_view_bounds(self):
        camera = self.camera
        # Camera vectors
        pos = np.array(camera.position)
        fp = np.array(camera.focal_point)
        up = np.array(camera.up)
        
        # Forward vector
        fwd = fp - pos
        fwd /= np.linalg.norm(fwd)
        
        # Right vector
        right = np.cross(fwd, up)
        right /= np.linalg.norm(right)
        
        # True up vector
        up = np.cross(right, fwd)
        
        # Near and far distances
        near, far = camera.clipping_range
        
        # Half heights and widths
        angle = np.deg2rad(camera.view_angle)
        near_height = 2 * np.tan(angle / 2) * near
        far_height = 2 * np.tan(angle / 2) * far
        
        aspect = 1.0  # Assume square viewport
        near_width = near_height * aspect
        far_width = far_height * aspect
        
        # Compute 4 corners of near and far planes
        def plane_corners(center, width, height):
            hw = width / 2
            hh = height / 2
            return np.array([
                center + (-right*hw + up*hh),  # top-left
                center + (right*hw + up*hh),   # top-right
                center + (right*hw - up*hh),   # bottom-right
                center + (-right*hw - up*hh),  # bottom-left
            ])
        
        near_center = pos + fwd * near
        far_center = pos + fwd * far
        
        near_corners = plane_corners(near_center, near_width, near_height)
        far_corners = plane_corners(far_center, far_width, far_height)
        
        # Combine all corners
        all_corners = np.vstack([near_corners, far_corners])
        
        # Axis-aligned bounds
        x_min, y_min, z_min = all_corners.min(axis=0)
        x_max, y_max, z_max = all_corners.max(axis=0)
        
        return (x_min, x_max, y_min, y_max, z_min, z_max)

    # ---------------------------------------------------------------
    # WRAPPER FOR QTINTERACTOR
    # ---------------------------------------------------------------
    def add_observer(self, event, callback):
        """Add a VTK observer to the plotter's interactor."""
        self.iren.add_observer(event, callback)

    # ---------------------------------------------------------------
    # DEBUGGING
    # ---------------------------------------------------------------
    def print_scene_objects(self, verbose=False):
        """Print all scene objects."""
        if CONFIG["DEBUG"]:
            if not self.scene_objects:
                print("No scene objects available.")
                return

            print("Scene Objects:")
            for name, obj in self.scene_objects.items():
                mesh = obj["mesh"]
                actor = obj["actor"]
                print(f" - {name}: mesh={type(mesh).__name__}, actor={type(actor).__name__}")
                if verbose:
                    inspect_actor(actor)
