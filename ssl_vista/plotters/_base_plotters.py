__all__ = [
    "BasePlotter",
    "BaseVisualPlotter",
    "BaseMplPlotter",
    ]

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PyQt5 import  QtCore, QtGui

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from ssl_vista import CONFIG
from .pv_utils.scene_objects import SceneObject
from .pv_utils.debug import inspect_actor

class BasePlotter:
    def __init__(self, **kwargs):
        self.widget = None

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


class BaseVisualPlotter(BasePlotter):
    """
    Base class for a PyVista QtInteractor Plotter.
    
    Subclasses MUST implement:
      - setup_scene(): initialize actors, camera, grid, etc.
      - reset_scene(): reset the scene to initial state
      - update_all_scene_objects(*args, **kwargs): update positions, orientations, etc.
    """

    def __init__(self, parent=None, context=None, **kwargs):
        super().__init__(**kwargs)
        self.context = context
        self.pvqt = QtInteractor(parent=parent)
        self.set_widget(self.pvqt)

        # - Dictionary storing all scene objects
        self.scene_objects = {} # dict of SceneObject

        # - Ensure proper focus so toolbars get keyboard input
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
    # PYVISTA QTINTERACTOR SHORTHCUTS
    # ---------------------------------------------------------------
    def reset_camera(self):
        return self.pvqt.reset_camera()

    # ---------------------------------------------------------------
    # KEY EVENT HANDLING
    # ---------------------------------------------------------------
    #TODO: Better key event handling
    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """Shadow all key presses to avoid default VTK behavior."""
        key = event.key()
        if key == QtCore.Qt.Key_R:
            self.pvqt.reset_camera()
        event.accept()  # Stop propagation to PyVista/VTK

    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        """Shadow all key releases."""
        event.accept()

    # ---------------------------------------------------------------
    # SCENE OBJECT MANAGEMENT
    # ---------------------------------------------------------------
    def add_scene_object(self, name: str, mesh: pv.MatrixLike = None, obj: SceneObject = None, visible=True, **kwargs):
        """
        Add a mesh to the scene and store it.
        
        Parameters
        ----------
        name : str
            Unique name for the object.
        mesh : pyvista.DataSet
            The mesh to add.
        obj : SceneObject
            The scene object to add.
        kwargs : dict
            Additional arguments passed to `add_mesh`.
        
        Returns
        -------
        mesh
        """
        if name in self.scene_objects:
            raise ValueError(f"Scene object '{name}' already exists.")

        if mesh is None and obj is None:
            raise ValueError("Either 'mesh' or 'obj' must be provided.")

        if obj is not None:
            actor = self.pvqt.add_mesh(obj.mesh, **kwargs)
            obj.actor = actor
            self.scene_objects[name] = obj
        else:
            actor = self.pvqt.add_mesh(mesh, **kwargs)
            actor.visibility = visible
            self.scene_objects[name] = SceneObject(actor=actor, mesh=mesh)

    def remove_scene_object(self, name: str):
        """Remove a scene object from the plotter."""
        if name in self.scene_objects:
            actor = self.scene_objects[name].actor
            self.pvqt.remove_actor(actor)
            del self.scene_objects[name]

    # ---------------------------------------------------------------
    # DEBUGGING
    # ---------------------------------------------------------------
    def print_scene_objects(self, verbose=False):
        """Print all scene objects."""
        if CONFIG["DEBUG"]:
            print("[DEBUG] BaseVisualPlotter Artists -----")
            if not self.scene_objects:
                print("No scene objects available.")
                return
            
            print("Scene Objects:")
            for name, obj in self.scene_objects.items():
                mesh = obj.mesh
                actor = obj.actor
                print(f" - {name}: mesh={type(mesh).__name__}, actor={type(actor).__name__}")
                if verbose:
                    inspect_actor(actor)
            print("---------------------------------------\n")

class BaseMplPlotter(BasePlotter):
    """
    Base class for Matplotlib-based plotters.
    
    Subclasses should:
        - define self.axes_config: dict specifying axes
        - implement init_artists(self)
        - implement update_artists(self, frame_data)
        - override compute_frame(self, frame_idx) if needed for large logs
    """

    def __init__(self, parent=None, context=None, figsize=(8,6), dpi=100):
        self.context = context
        
        # -- To be defined by subclass !!
        # e.g., {"main": {"positions":[0,0,1,1], "projection":"3d"}}
        self.axes_config = {} 
        # ----------------------------

        self.figsize, self.dpi = figsize, dpi
        self.fig = plt.figure(figsize=figsize, dpi=dpi)
        self.axes = {}
        self._initialized = False

        # Embed in Qt if parent provided
        self.canvas = FigureCanvas(self.fig)
        if parent:
            self.canvas.setParent(parent)
        self.widget = self.canvas

    def set_widget(self, widget):
        """Set the Qt widget for layouts."""
        self.widget = widget

    def get_widget(self):
        """Return the Qt widget for layouts."""
        return self.widget

    def setup_scene(self):
        """Create axes and initialize artists."""
        if not self._initialized:
            self._setup_axes()
            self._initialized = True
            self.fig.canvas.draw_count = 0  # reset draw count

            if CONFIG["DEBUG"]:
                print(f"[DEBUG] Scene setup complete.\n")

    def reset_scene(self, sim_data, sim_settings):
        """Reset the scene to its initial state."""
        # Clear all artists from the axes
        for ax in self.axes.values():
            ax.cla()

        # Reinitialize artists
        self.init_artists(sim_data, sim_settings)
        self.fig.canvas.draw_count = 0  # reset draw count

        if CONFIG["DEBUG"]:
            self.debug_artists()

    def update_all_scene_objects(self, sim_data, idx):
        """Update all artists in the scene."""
        self.update_artists(sim_data, idx)
    
    # ---------------------------------------------------------------
    # ABSTRACT METHODS (must be implemented)
    # ---------------------------------------------------------------
    def init_artists(self, sim_data, sim_settings):
        """Initialize all plot elements. Must be implemented by subclass."""
        raise NotImplementedError
    
    def update_artists(self, sim_data, idx):
        """Update plot elements for a new frame. Must be implemented by subclass."""
        raise NotImplementedError
    
    # ---------------------------------------------------------------
    # SETUP
    # ---------------------------------------------------------------
    def _setup_axes(self):
        """Create axes based on self.axes_config."""
        for key, cfg in self.axes_config.items():
            cfg_copy = cfg.copy()  # avoid modifying the original config

            # Extract rect/position
            rect = None
            if "position" in cfg_copy:
                rect = cfg_copy.pop("position")
            if "rect" in cfg_copy:
                if rect is not None:
                    raise ValueError(f"Axis '{key}': Cannot provide both 'rect' and 'position'.")
                rect = cfg_copy.pop("rect")
            if rect is None:
                raise ValueError(f"Axis '{key}': Must provide either 'position' or 'rect'.")

            # Create axis with remaining kwargs (e.g., projection)
            self.axes[key] = self.fig.add_axes(rect, **cfg_copy)

            if CONFIG.get("DEBUG", False):
                print(f"[DEBUG] Created axis '{key}' with rect={rect} and kwargs={cfg_copy}")

    # ---------------------------------------------------------------
    # DEBUG UTILITIES
    # ---------------------------------------------------------------

    def debug_artists(self):
        """
        Print all artists in each axis with their key and type.
        Useful to inspect plot elements during development.
        """
        
        print("[DEBUG] BaseMplPlotter Artists Debug -----")
        total_count = 0

        def count_and_print(artist, prefix=""):
            """Recursively print and count artists."""
            nonlocal total_count
            if isinstance(artist, dict):
                for k, v in artist.items():
                    count_and_print(v, prefix=f"{prefix}[{k}]")
            elif isinstance(artist, list):
                for i, a in enumerate(artist):
                    count_and_print(a, prefix=f"{prefix}[{i}]")
            elif isinstance(artist, np.ndarray):
                print(f"{prefix} np.ndarray shape={artist.shape}, dtype={type(artist.flat[0]).__name__}")
                total_count += artist.size
            else:
                print(f"{prefix} {type(artist).__name__}: {artist}")
                total_count += 1

        for ax_key, ax in self.axes.items():
            print(f"Axis '{ax_key}' ({type(ax).__name__}):")
            group = ax.get_children()
            if not group:
                print(f"    [!] No artists in axis '{ax_key}'")
                continue
            count_and_print(group, prefix="    ")

        print(f"Total artists: {total_count}")
        print("------------------------------------------\n")
