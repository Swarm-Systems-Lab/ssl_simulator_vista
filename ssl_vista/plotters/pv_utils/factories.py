__all__ = ["RobotFactory"]

import numpy as np
import pyvista as pv

import numpy as np
import pyvista as pv


class RobotFactory:
    """
    Factory that creates simple PyVista meshes representing different robot types.
    Automatically handles 2D and 3D versions depending on context.
    """

    def __init__(self, dimension=2):
        """
        Parameters
        ----------
        dimension : int
            2 for 2D shapes (XY plane), 3 for 3D shapes.
        """
        self.dimension = dimension

    def create(self, robot_type="default", **kwargs):
        """Return a simple PolyData mesh for the specified robot type."""
        if self.dimension == 3:
            mesh = self._create_3d(robot_type, **kwargs)
        else:
            mesh = self._create_2d(robot_type, **kwargs)
        return self._bound_to_unit_cube(mesh)

    # ------------------------------------------------------------------
    # 2D SHAPES
    # ------------------------------------------------------------------
    def _create_2d(self, robot_type, **kwargs):
        if robot_type in ["single_integrator", "default"]:
            # Simple disk
            theta = np.linspace(0, 2 * np.pi, 50)
            verts = np.c_[np.cos(theta) * 0.25, np.sin(theta) * 0.25]
            faces = [len(verts)] + list(range(len(verts)))

        elif robot_type == "unicycle":
            # Simple triangle pointing in +X direction
            verts = np.array([[0.5, 0], [0, 0.25], [0, -0.25]])
            faces = [3, 0, 1, 2]

        elif robot_type == "car":
            # Simple rectangle pointing in +X direction
            verts = np.array([[-0.4, -0.2], [0.4, -0.2], [0.4, 0.2], [-0.4, 0.2]])
            faces = [4, 0, 1, 2, 3]

        elif robot_type == "fixed_wing":
            verts = np.array([[0.5, 0], [-0.5, 0.25], [-0.5, -0.25], [0, 0]])
            faces = [4, 0, 1, 3, 2]

        else:
            raise ValueError(f"Unknown 2D robot type '{robot_type}'")

        mesh = pv.PolyData()
        mesh.points = np.hstack([verts, np.zeros((verts.shape[0], 1))])
        mesh.faces = np.hstack([faces])
        return mesh

    # ------------------------------------------------------------------
    # 3D SHAPES
    # ------------------------------------------------------------------
    def _create_3d(self, robot_type, **kwargs):
        if robot_type in ["single_integrator", "default"]:
            # Simple sphere
            mesh = pv.Sphere(radius=0.25, theta_resolution=32, phi_resolution=24)

        elif robot_type == "unicycle":
            # Small cone on top of a disk base, , pointing along +X
            body = pv.Disc(inner=0.0, outer=0.1, normal=(1, 0, 0), r_res=1, c_res=60)
            cone = pv.Cone(
                center=(0.2, 0, 0),   # shift it so it sits nicely on the disc
                direction=(1, 0, 0),  # <-- point along +X
                height=0.4,
                radius=0.1,
                resolution=50
            )
            mesh = body.merge(cone)

        elif robot_type == "car":
            # Box-like car
            mesh = pv.Cube(center=(0, 0, 0.1), x_length=0.6, y_length=0.3, z_length=0.2)

        elif robot_type == "quadrotor":
            # Four small spheres (propellers) + a main body
            arm_len = 0.3
            body = pv.Sphere(radius=0.1, theta_resolution=24, phi_resolution=16)
            prop = pv.Sphere(radius=0.05, theta_resolution=12, phi_resolution=12)
            prop_positions = [
                (arm_len, arm_len, 0),
                (-arm_len, arm_len, 0),
                (-arm_len, -arm_len, 0),
                (arm_len, -arm_len, 0),
            ]
            all_meshes = [body]
            for pos in prop_positions:
                all_meshes.append(prop.copy().translate(pos))
            mesh = pv.MultiBlock(all_meshes).combine()

        else:
            raise ValueError(f"Unknown 3D robot type '{robot_type}'")
        return mesh

    def _bound_to_unit_cube(self, mesh):
        """Scale and translate the mesh to fit within a 1x1x1 cube."""
        bounds = np.array(mesh.bounds).reshape(3, 2)

        scales = np.ones(3)
        if self.dimension == 2:
            scales[0:2] = scales[0:2] = 1 / (bounds[0:2, 1] - bounds[0:2, 0])
        else:
            scales = 1 / (bounds[:, 1] - bounds[:, 0])

        scale_factor = scales.min()
        center = bounds.mean(axis=1)
        mesh.scale([scale_factor] * 3, inplace=True)
        mesh.translate(-center * scale_factor, inplace=True)
        return mesh
