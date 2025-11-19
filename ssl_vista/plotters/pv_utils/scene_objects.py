__all__ = [
    "Icon2D",
    "Icon3D",
    "Line",
    "StraightLine",
    "Vector",
    "Axes",
    "Robot2D",
    "Robot3D",
    "SphereGrid",
    "VectorField"
]

from calendar import c
import numpy as np
import pyvista as pv
from typing import Union

from ssl_vista import CONFIG
GCONF = CONFIG["GRAPHICS"]

from .factories import RobotFactory

pv.global_theme.allow_empty_mesh = True

class SceneObject:
    def __init__(self, mesh: pv.DataSet, actor: pv.Actor = None, size: float = 1.0, **style):
        """
        A base class for scene objects that encapsulates a mesh and its actor.

        Parameters
        ----------
        mesh : pv.DataSet
            The mesh representing the geometry of the object.
        actor : pv.Actor, optional
            The actor associated with the mesh for rendering.
        """
        self.mesh = mesh
        self.actor = actor
        self.default_color = None
        self.default_centroid = mesh.center

        if size != 1.0:
            self.scale(size)
        self.default_mesh = mesh.copy()

        self.style = style

    # ---------------------------------------------------------------
    # METHODS WHICH CAN BE OVERIDDEN BY SUBCLASSES
    # ---------------------------------------------------------------

    def set_focus(self, focused: bool):
        """Set the object as focused (e.g., change color to indicate focus)."""
        if focused:
            self.set_color("red")
        else:
            self.reset_color()

    # ---------------------------------------------------------------

    def set_color(self, color: pv.ColorLike):
        """Set the color of the object."""
        if self.actor is not None:
            if self.default_color is None:
                self.default_color = self.actor.prop.color
            self.actor.prop.color = color

    def set_opacity(self, opacity: float):
        """Set the opacity of the object."""
        if self.actor is not None:
            self.actor.prop.opacity = opacity

    def set_visibility(self, visible: bool):
        """Set the visibility of the object."""
        if self.actor is not None:
            self.actor.visibility = visible

    def reset_color(self):
        """
        Reset the color of the object to its default color.
        """
        if self.actor is not None and self.default_color is not None:
            self.actor.prop.color = self.default_color

    def is_visible(self) -> bool:
        """Check if the object is currently visible."""
        return self.actor.visibility if self.actor is not None else False
    
    def transform(
            self, 
            translation: np.ndarray = None, 
            R: np.ndarray = None, 
            scale_factor: float = None, 
            center: np.ndarray = None
        ):
        """
        Apply translation, rotation, and scaling to the object.

        Parameters
        ----------
        translation : np.ndarray, optional
            3D translation vector [dx, dy, dz]
        R : np.ndarray, optional
            3x3 rotation matrix.
        scale_factor : float, optional
            Uniform scaling factor.
        center : np.ndarray, optional
            3D center point for rotation and scaling. If None, uses the mesh's geometric center.
        """
        pts = self.default_mesh.copy().points
        if center is None and (R is not None or scale_factor is not None):
            center = self.default_centroid
        if R is not None:
            pts = (R @ (pts - center).T).T + center
        if scale_factor is not None:
            pts = (pts - center) * scale_factor + center
        if translation is not None:
            pts += translation
        self.update_mesh_points(pts)
    
    def translate(self, translation: np.ndarray):
        """
        Translate all children by the given vector.
        
        Parameters
        ----------
        translation : np.ndarray
            3D translation vector [dx, dy, dz]
        """
        if self.mesh is not None:
            new_points = self.mesh.points + translation
            self.update_mesh_points(new_points)
    
    def rotate(self, R: np.ndarray, center: np.ndarray = None):
        """
        Rotate the object around a center point using the given rotation matrix.

        Parameters
        ----------
        R : np.ndarray
            3x3 rotation matrix.
        center : np.ndarray, optional
            3D center of rotation. If None, uses the mesh's geometric center.
        """
        if self.mesh is not None:
            if center is None:
                center = self.default_centroid
            pts = self.mesh.points
            new_points = (R @ (pts - center).T).T + center
            self.update_mesh_points(new_points)
    
    def scale(self, scale_factor: float, center: np.ndarray = None):
        """
        Scale the object uniformly from a center point.

        Parameters
        ----------
        scale_factor : float
            Uniform scaling factor.
        center : np.ndarray, optional
            3D center of scaling. If None, uses the mesh's geometric center.
        """
        if self.mesh is not None:
            if center is None:
                center = self.default_centroid
            pts = self.mesh.points
            new_points = (pts - center) * scale_factor + center
            self.update_mesh_points(new_points)

    def update_mesh(self, new_mesh: pv.DataSet):
        """Update the mesh of the object."""
        self.mesh = new_mesh
        if self.actor is not None:
            self.actor.mapper.dataset = new_mesh
            self.actor.mapper.Modified()

    def update_mesh_points(self, new_points: np.ndarray):
        """Update only the points of the mesh."""
        if self.mesh is not None and self.mesh.n_points == new_points.shape[0]:
            self.mesh.points = new_points
            self.mesh.Modified()
            if self.actor is not None:
                self.actor.mapper.Modified()

    def update_mesh_lines(self, new_lines: np.ndarray):
        """Update only the lines of the mesh."""
        if self.mesh is not None:
            self.mesh.lines = new_lines
            self.mesh.Modified()
            if self.actor is not None:
                self.actor.mapper.Modified()

class SceneObjectBundle:
    """
    A composite container for multiple related SceneObjects that should be 
    managed, transformed, or styled together.
    
    This allows you to:
    - Group multiple meshes into a single logical unit
    - Apply transformations (translate, rotate, scale) to all children
    - Control visibility of the entire bundle
    - Access individual children by name for fine-grained control
    
    Example:
        bundle = SceneObjectBundle()
        bundle.add_child("grid", SceneObject(mesh1), color="grey")
        bundle.add_child("sphere", SceneObject(mesh2), color="blue", opacity=0.5)
        
        # Later, transform the entire bundle
        bundle.translate([1, 0, 0])
        bundle.set_visibility(False)
    """
    
    def __init__(self):
        self.children = {}  # name -> {"obj": SceneObject, "style": dict}
        self._original_centroids = {}  # store original positions for transforms

    # ---------------------------------------------------------------
    # METHODS WHICH CAN BE OVERIDDEN BY SUBCLASSES
    # ---------------------------------------------------------------

    def set_focus(self, focused: bool):
        """Set the object as focused (e.g., change color to indicate focus)."""
        for child_data in self.children.values():
            child_data["obj"].set_focus(focused)

    # ---------------------------------------------------------------

    def add_child(self, name: str, obj: Union[SceneObject, 'SceneObjectBundle'], set_color=True, **style_kwargs):
        """
        Add a child SceneObject or SceneObjectBundle to the bundle.

        Parameters
        ----------
        name : str
            Unique identifier for this child object or bundle.
        obj : SceneObject or SceneObjectBundle
            The scene object or bundle to add.
        **style_kwargs : dict
            Style properties (color, opacity, line_width, etc.)
        """
        if name in self.children:
            raise ValueError(f"Child '{name}' already exists in bundle")

        self.children[name] = {
            "obj": obj,
            "set_color": set_color,
            "style": style_kwargs
        }

        # Store original centroid for transforms if the object is a SceneObject
        if isinstance(obj, SceneObject) and obj.mesh is not None and obj.mesh.n_points > 0:
            self._original_centroids[name] = obj.default_centroid

    def get_child(self, name: str) -> SceneObject:
        """Get a specific child object by name."""
        if name not in self.children:
            raise KeyError(f"Child '{name}' not found in bundle")
        return self.children[name]["obj"]
    
    def set_visibility(self, visible: bool):
        """Set visibility for all children in the bundle."""
        for child_data in self.children.values():
            child_data["obj"].set_visibility(visible)
    
    def set_color(self, color: pv.ColorLike):
        """Set color for all children in the bundle."""
        for child_data in self.children.values():
            if child_data["set_color"]:
                child_data["obj"].set_color(color)
    
    def reset_color(self):
        """Reset color for all children in the bundle."""
        for child_data in self.children.values():
            if child_data["set_color"]:
                child_data["obj"].reset_color()

    def transform(self, translation: np.ndarray = None, R: np.ndarray = None, scale_factor: float = None, center: np.ndarray = None):
        """
        Apply translation, rotation, and scaling to all children.

        Parameters
        ----------
        translation : np.ndarray, optional
            3D translation vector [dx, dy, dz].
        R : np.ndarray, optional
            3x3 rotation matrix.
        scale_factor : float, optional
            Uniform scaling factor.
        center : np.ndarray, optional
            3D center point for rotation and scaling. If None, uses bundle's geometric center.
        """
        if center is None and (R is not None or scale_factor is not None):
            # Compute bundle center from all meshes
            center = self._compute_bundle_center()
        else:
            center = np.asarray(center, dtype=float)

        for child_data in self.children.values():
            obj = child_data["obj"]
            obj.transform(translation=translation, R=R, scale_factor=scale_factor, center=center)

    def translate(self, translation: np.ndarray):
        """
        Translate all children by the given vector.
        
        Parameters
        ----------
        translation : np.ndarray
            3D translation vector [dx, dy, dz]
        """
        translation = np.asarray(translation, dtype=float)
        for name, child_data in self.children.items():
            obj = child_data["obj"]
            obj.translate(translation)
    
    def rotate(self, R: np.ndarray, center: np.ndarray = None):
        """
        Rotate all children around a center point.
        
        Parameters
        ----------
        R : np.ndarray
            3x3 rotation matrix
        center : np.ndarray, optional
            3D center of rotation. If None, uses bundle's geometric center.
        """
        if center is None:
            # Compute bundle center from all meshes
            center = self._compute_bundle_center()
        
        R = np.asarray(R, dtype=float)
        center = np.asarray(center, dtype=float)
        
        for child_data in self.children.values():
            obj = child_data["obj"]
            obj.rotate(R, center)
    
    def scale(self, scale_factor: float, center: np.ndarray = None):
        """
        Scale all children uniformly from a center point.

        Parameters
        ----------
        scale_factor : float
            Uniform scaling factor
        center : np.ndarray, optional
            3D center of scaling. If None, uses bundle's geometric center.
        """
        if center is None:
            # Compute bundle center from all meshes
            center = self._compute_bundle_center()
        
        center = np.asarray(center, dtype=float)
        
        for child_data in self.children.values():
            obj = child_data["obj"]
            obj.scale(scale_factor, center)

    def _compute_bundle_center(self) -> np.ndarray:
        """Compute the geometric center of the entire bundle."""
        all_points = []
        for child_data in self.children.values():
            obj = child_data["obj"]
            if isinstance(obj, SceneObjectBundle):
                # Recursively compute the center for nested bundles
                center = obj._compute_bundle_center()
                all_points.append(center)
            elif obj.mesh is not None and obj.mesh.n_points > 0:
                all_points.append(obj.mesh.points)
        if all_points:
            return np.vstack(all_points).mean(axis=0)
        else:
            return np.array([0.0, 0.0, 0.0])
        
    def __len__(self):
        return len(self.children)
    
    def __iter__(self):
        """Iterate over (name, SceneObject) pairs."""
        for name, child_data in self.children.items():
            yield name, child_data["obj"]
    
    def __getitem__(self, name: str) -> Union[SceneObject, 'SceneObjectBundle']:
        """Allow indexing to retrieve a child object by name."""
        return self.get_child(name)

# ------------------------------------------------------------------
# SPECIFIC SCENE OBJECTS
# ------------------------------------------------------------------

class Icon2D(SceneObject):
    def __init__(self, robot_type: str, **kwargs):
        self.robot_factory = RobotFactory(dimension=2)
        mesh_robot = self.robot_factory.create(robot_type)
        super().__init__(mesh=mesh_robot, **kwargs)
    
    def transform_to(self, centroid: np.ndarray = None,  heading: float = None):
        """
        Transforms the object to a new position and orientation based on the specified
        centroid and heading. The transformation involves a translation and an optional
        rotation around the object's default centroid.
        Args:
            centroid (np.ndarray, optional): A 2D array-like object representing the target
                centroid (x, y) in the plane. If None, no translation is applied.
            heading (float, optional): A scalar angle in radians representing the target
                orientation. If None, no rotation is applied.
        Behavior:
            - If `centroid` is provided, the object is translated such that its default
              centroid aligns with the specified target centroid.
            - If `heading` is provided, the object is rotated around its default centroid
              by the specified angle.
            - If both `centroid` and `heading` are provided, the object undergoes both
              transformations in sequence.
        Notes:
            - The transformation is applied relative to the object's default centroid.
            - The rotation matrix is constructed using the specified heading angle.
        """
        if centroid is None:
            translation = np.zeros(3)
        else:
            # compute translation vector (target centroid - original centroid)
            centroid = np.hstack([np.asarray(centroid), 0])
            translation = centroid - self.default_centroid

        if heading is None:
            R = None
        else:
            R = np.array([
                [np.cos(heading), -np.sin(heading), 0],
                [np.sin(heading), np.cos(heading), 0],
                [0, 0, 1]
            ])

        # Apply transform (rotation R around orig_centroid then translation)
        self.transform(translation=translation, R=R, center=self.default_centroid)

class Icon3D(SceneObject):
    def __init__(self, robot_type: str, **kwargs):
        self.robot_factory = RobotFactory(dimension=3)
        mesh_robot = self.robot_factory.create(robot_type)

        # ensure mesh has 3D points (factory may give 2D -> ensure z column exists)
        pts = np.asarray(mesh_robot.points)
        if pts.shape[1] == 2:
            mesh_robot.points = np.hstack([pts, np.zeros((pts.shape[0], 1))])

        super().__init__(mesh=mesh_robot, **kwargs)

    def transform_to(self, centroid: np.ndarray = None, R: np.ndarray = None):
        """
        Transforms the object to a new position and orientation based on the specified
        target centroid and rotation matrix. The transformation involves a translation
        and an optional rotation around the object's default centroid.

        Args:
            centroid (np.ndarray, optional): A 1D array-like object of shape (3,) 
            representing the target centroid (x, y, z). If None, no translation 
            is applied.
            R (np.ndarray, optional): A 3x3 rotation matrix representing the target 
            orientation. If None, no rotation is applied.

        Behavior:
            - If `centroid` is provided, the object is translated such that its default
              centroid aligns with the specified target centroid.
            - If `R` is provided, the object is rotated around its default centroid
              using the specified rotation matrix.
            - If both `centroid` and `R` are provided, the object undergoes both
              transformations in sequence.

        Notes:
            - The transformation is applied relative to the object's default centroid.
            - The translation vector is computed as the difference between the target
              centroid and the object's default centroid.
        """
        if centroid is None:
            translation = np.zeros(3)
        else:
            # compute translation vector (target centroid - original centroid)
            original_centroid = np.asarray(self.default_centroid)
            translation = np.asarray(centroid) - original_centroid

        # Apply transform (rotation R around orig_centroid then translation)
        self.transform(translation=translation, R=R, center=original_centroid)

class Line(SceneObject):
    def __init__(self, points=None, **kwargs):
        if points is None:
            line = pv.PolyData()
            line.points = np.empty((0, 3))
            line.lines = np.empty((0,), dtype=int)
        else:
            line = self._gen_line_from_points(points)
        super().__init__(mesh=line, **kwargs)
    
    def set_points(self, new_points: np.ndarray):
        line_mesh = self._gen_line_from_points(new_points)
        self.update_mesh(line_mesh)
    
    def _gen_line_from_points(self, points: np.ndarray) -> pv.PolyData:
        n_pts = points.shape[0]
        
        # Ensure points are 3D by adding a zero z-coordinate if they are 2D
        if points.shape[1] == 2:
            points = np.hstack([points, np.zeros((n_pts, 1))])
        if n_pts > 1:
            lines = np.hstack([[2, i, i + 1] for i in range(n_pts - 1)]).astype(np.int64)
        else:
            lines = np.empty((0,), dtype=np.int64)
        line = pv.PolyData()
        line.points = points
        line.lines = lines
        return line

class StraightLine(SceneObject):
    def __init__(self, start: np.ndarray, end: np.ndarray, **kwargs):
        line = pv.Line(start, end)
        super().__init__(mesh=line, **kwargs)

class Vector(SceneObject):
    """This class is a wrapper of the pv.Arrow object made for better integration"""

    def __init__(self, origin: np.ndarray, direction: np.ndarray, scale: float = 1.0, **kwargs):
        """
        Create a vector object.

        Parameters
        ----------
        origin : np.ndarray
            A 1D array of shape (3,) representing the starting point of the vector.
        direction : np.ndarray
            A 1D array of shape (3,) representing the direction and magnitude of the vector.
        scale : float
            A scaling factor for the arrow.
        **kwargs : dict
            Additional styling arguments for the arrow.
        """
        self.scale = scale
        arrow = pv.Arrow(start=origin, direction=direction, scale=self.scale)
        super().__init__(mesh=arrow, **kwargs)

    def update_vector(self, origin: np.ndarray, direction: np.ndarray):
        """
        Update the origin, direction, and optionally the scale of the vector.

        Parameters
        ----------
        origin : np.ndarray
            A 1D array of shape (3,) representing the new starting point of the vector.
        direction : np.ndarray
            A 1D array of shape (3,) representing the new direction and magnitude of the vector.
        scale : float, optional
            A new scaling factor for the arrow. If None, the current scale is used.
        """
        arrow = pv.Arrow(start=origin, direction=direction, scale=self.scale)
        self.update_mesh(arrow)

# ------------------------------------------------------------------
# COMPOSITE/BUNDLE SCENE OBJECTS
# ------------------------------------------------------------------

class Axes(SceneObjectBundle):
    """
    A bundle representing the x, y, z attitude vectors (axes).
    """

    def __init__(
            self, 
            origin = np.array([0.0, 0.0, 0.0]), 
            size: float = 1.0,
            axis_colors = {"x": "red", "y": "green", "z": "blue"},
            **kwargs
        ):
        """
        Create the initial x, y, z attitude vectors.
        """
        super().__init__()
        self.origin = origin
        self.axis_colors = axis_colors
        self.size = size

        kwargs["line_width"] = kwargs.get("line_width", GCONF["AXES_LINE_WIDTH"] * size)

        for i, (label, color) in enumerate(self.axis_colors.items()):
            end = self.origin + self.size * np.eye(3)[i]
            line = StraightLine(self.origin, end)
            self.add_child(label, line, color=color, **kwargs)

    def transform_to(self, centroid: np.ndarray = None, R: np.ndarray = None):
        """
        Update the attitude axes according to the given rotation matrix.

        Parameters
        ----------
        R : np.ndarray
            3x3 rotation matrix.
        """
        origin = self.origin if centroid is None else centroid

        if R is None:
            for label in ["x", "y", "z"]:
                obj = self.get_child(label)
                obj.transform(translation = (origin - self.origin))
        else:
            vectors = origin[:,None] + R * self.size
            axes = {"x": vectors[:, 0], "y": vectors[:, 1], "z": vectors[:, 2]}

            for label, vec in axes.items():
                obj = self.get_child(label)
                new_pts = np.array([origin, vec])
                obj.update_mesh_points(new_pts)

class Robot2D(SceneObjectBundle):
    """
    A pre-configured bundle for a 3D robot mesh with attitude axes.
    This bundle contains:
        - The robot mesh (Icon3D)
        - The robot trajectory (Line)
    
    Example usage:
        robot_bundle = Robot2D(robot_type="unicycle", color="blue")
        plotter.add_scene_object("robot", robot_bundle)
    """
    
    def __init__(
            self, 
            robot_type: str = "default", 
            size: float = 1.0,
            **kwargs
        ):
        """
        Create a robot bundle with a 3D icon and attitude axes.
        
        Parameters
        ----------
        robot_type : str
            Type of robot icon to create (passed to Icon3D).
        color : str
            Color of the robot mesh.
        axes : bool
            Whether to include attitude axes.
        """
        super().__init__()
        
        # Create robot icon
        self.icon = Icon2D(robot_type=robot_type, size=size)

        # Create trajectory line
        self.traj = Line()
        
        # Add children with their styling
        self.add_child("trajectory", self.traj, line_width=GCONF["ROBOT_TRAJECTORY_SIZE"]*size, **kwargs)
        self.add_child("icon", self.icon, **kwargs)
    
    def transform_to(self, centroid: np.ndarray, heading: float = None):
        self.icon.transform_to(centroid, heading)
    
    def set_traj_points(self, new_points: np.ndarray):
        self.traj.set_points(new_points)

class Robot3D(SceneObjectBundle):
    """
    A pre-configured bundle for a 3D robot mesh with attitude axes.
    This bundle contains:
        - The robot mesh (Icon3D)
        - The robot trajectory (Line)
        - The attitude axes (Axes)
    
    Example usage:
        robot_bundle = Robot3D(robot_type="unicycle", color="blue")
        plotter.add_scene_object("robot", robot_bundle)
    """
    
    def __init__(self, 
            robot_type: str = "default", 
            axes: bool = True,
            size: float = 1.0,
            **kwargs
        ):
        """
        Create a robot bundle with a 3D icon and attitude axes.
        
        Parameters
        ----------
        robot_type : str
            Type of robot icon to create (passed to Icon3D).
        color : str
            Color of the robot mesh.
        axes : bool
            Whether to include attitude axes.
        """
        super().__init__()
        
        # Create robot icon
        self.icon = Icon3D(robot_type=robot_type, size=size)
        # self.icon.set_color(color)
        self.add_child("icon", self.icon, **kwargs)

        # Create trajectory line
        self.traj = Line()
        self.add_child("trajectory", self.traj, line_width=GCONF["ROBOT_TRAJECTORY_SIZE"]*size, **kwargs)

        # Create attitude axes
        if axes:
            self.axes = Axes(size=size)
            self.add_child("axes", self.axes, set_color=False, **kwargs)
        else:
            self.axes = None
        
    def transform_to(self, centroid: np.ndarray, R: np.ndarray = None):
        self.icon.transform_to(centroid, R)
        if self.axes is not None:
            self.axes.transform_to(centroid, R)
    
    def set_traj_points(self, new_points: np.ndarray):
        self.traj.set_points(new_points)
    
class SphereGrid(SceneObjectBundle):
    """
    A pre-configured bundle for the sphere grid visualization used in 
    the 3D attitude plotter. This creates a composite object with:
    - Fine grid lines (latitude/longitude)
    - Bold axis lines (at lat=90)
    - Geodesic lines (solid and dashed)
    - Optional transparent sphere
    
    Example usage:
        from .pv_utils.meshes import create_sphere_grid, create_geodesic, make_dashed_line
        
        sphere_bundle = SphereGrid(radius=1.0)
        
        # Add to plotter
        plotter.add_scene_object("sphere_grid", sphere_bundle)
    """
    
    def __init__(
            self, 
            radius: float = 1.0, 
            show_geodesics: bool = True, 
            lw: float = 3.0,
            lw_minor: float = 1.0,
            **kwargs
        ):
        """
        Create a sphere grid bundle with all components.
        
        Parameters
        ----------
        radius : float
            Radius of the sphere
        """
        super().__init__()
        
        # Import here to avoid circular dependency
        from .meshes import create_sphere_grid, create_geodesic, make_dashed_line
        
        # Create all mesh components
        mesh1 = create_sphere_grid(radius=radius, lat_step=15, lon_step=15)

        lat_mid = create_sphere_grid(radius=radius, lat_step=90, lon_step=None)
        if show_geodesics:
            geo_line1 = create_geodesic((-89.9, 0), (90, 0), radius=radius, n_points=40)
            geo_line1_dashed = create_geodesic((-90.1, 0), (90, 0), radius=radius, n_points=60)
            geo_line1_dashed = make_dashed_line(geo_line1_dashed, dash_length=3)
            
            geo_line2 = create_geodesic((-89.9, 90), (90, 90), radius=radius, n_points=40)
            geo_line2_dashed = create_geodesic((-90.1, 90), (90, 90), radius=radius, n_points=60)
            geo_line2_dashed = make_dashed_line(geo_line2_dashed, dash_length=2)
        else:
            lon_mid = create_sphere_grid(radius=radius, lat_step=None, lon_step=90)
        
        sphere = pv.Sphere(radius=radius, theta_resolution=30, phi_resolution=30)
        
        # Add children with their styling
        kw_markers_main = {"line_width": lw, **kwargs}
        kw_markers = {"line_width": lw_minor, **kwargs}
        
        self.add_child("fine_grid", SceneObject(mesh1), color="grey", **kw_markers)
        self.add_child("lat_mid", SceneObject(lat_mid), color="black", **kw_markers_main)
        if show_geodesics:
            self.add_child("geo_line1", SceneObject(geo_line1), color="black", **kw_markers_main)
            self.add_child("geo_line1_dashed", SceneObject(geo_line1_dashed), color="black", **kw_markers_main)
            self.add_child("geo_line2", SceneObject(geo_line2), color="black", **kw_markers_main)
            self.add_child("geo_line2_dashed", SceneObject(geo_line2_dashed), color="black", **kw_markers_main)
        else:
            self.add_child("lon_mid", SceneObject(lon_mid), color="black", **kw_markers_main)

        self.add_child("sphere", SceneObject(sphere), color="lightgray", opacity=0.05)

class VectorField(SceneObjectBundle):
    """
    A bundle representing a vector field using arrows.
    Each arrow represents a vector at a specific position.
    """

    def __init__(
            self, 
            vectors: np.ndarray, 
            origins: np.ndarray = None, 
            scale: float = 1.0, 
            **kwargs
        ):
        """
        Create a vector field bundle.

        Parameters
        ----------
        vectors : np.ndarray
            An array of shape (N, 3) representing the vectors.
        origins : np.ndarray, optional
            An array of shape (N, 3) representing the origins of the vectors.
            If None, all vectors originate from the origin (0, 0, 0).
        scale : float
            A scaling factor for the arrows.
        **kwargs : dict
            Additional styling arguments for the arrows.
        """
        super().__init__()
        self.scale = scale

        if origins is None:
            origins = np.zeros_like(vectors)
    
        vectors = np.atleast_2d(vectors)
        origins = np.atleast_2d(origins)

        if vectors.shape != origins.shape:
            raise ValueError("Vectors and origins must have the same shape.")

        for i, (origin, vector) in enumerate(zip(origins, vectors)):
            arrow = pv.Arrow(start=origin, direction=vector, scale=self.scale)
            self.add_child(f"arrow_{i}", SceneObject(mesh=arrow), **kwargs)

    def update_vectors(self, vectors: np.ndarray, origins: np.ndarray = None):
        """
        Update the vectors and origins of the vector field.

        Parameters
        ----------
        vectors : np.ndarray
            An array of shape (N, 3) representing the new vectors.
        origins : np.ndarray, optional
            An array of shape (N, 3) representing the new origins of the vectors.
            If None, the origins remain unchanged.
        """
        if origins is None:
            origins = np.zeros_like(vectors)

        vectors = np.atleast_2d(vectors)
        origins = np.atleast_2d(origins)

        if vectors.shape != origins.shape:
            raise ValueError("Vectors and origins must have the same shape.")

        for i, (origin, vector) in enumerate(zip(origins, vectors)):
            arrow = pv.Arrow(start=origin, direction=vector, scale=self.scale)
            child_name = f"arrow_{i}"
            if child_name in self.children:
                self.get_child(child_name).update_mesh(arrow)
            else:
                self.add_child(child_name, SceneObject(mesh=arrow))