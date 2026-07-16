# Plotter development

This guide explains how to add custom plotters to `ssl_vista`.

## The authoring contract (all backends)

Every plotter — PyVista, Matplotlib, and any future backend (e.g. pyqtgraph) — is
authored by implementing the **same two extension points**:

- `init_artists(self, sim_data, sim_settings)` — create the scene's artists from data.
- `update_artists(self, sim_data, idx)` — update them for frame `idx`.

The framework lifecycle methods that the grid driver actually calls
(`setup_scene`, `reset_scene`, `update_all_scene_objects`) are provided by the backend
base class and wired to `init_artists` / `update_artists` for you:

- `reset_scene` -> clears existing artists, calls `init_artists`, fits the camera.
- `update_all_scene_objects` -> calls `update_artists`, then renders.

You normally only override `setup_scene` (one-time, data-independent camera/lights/grid).
This uniform shape is what lets a new backend base class drop in and reuse existing
plotter authoring code.

## PyVista plotters

Inherit from `_BaseVisualPlotter`, or from `BaseCanvasPlotter` for built-in robot/grid
helpers (`add_robot`, `set_grid_centroid`, a `CanvasGrid`).

Implement `init_artists` / `update_artists` (and optionally `setup_scene`). Build the
scene from **scene objects** (see below) rather than calling `pvqt.add_mesh` directly.

## Matplotlib plotters

Inherit from `BaseMplPlotter`. Implement `init_artists` / `update_artists`, define
`self.axes_config` in `__init__`, and use `register_lines(...)` for time-series lines.

## Minimal Matplotlib example

A working example is provided in:

- `src/ssl_vista/data/grid_layouts/mpl_example.py`
- `src/ssl_vista/data/grid_layouts/example_mpl.json`

The layout entry points to a module file and class:

```json
{
  "type": "BaseMplPlotter",
  "module_path": "mpl_example.py",
  "class_name": "PlotterMplExample"
}
```

## Scene objects and poses (PyVista)

A **scene object** wraps a PyVista mesh and its VTK actor. Rigid objects carry a
**pose** applied through `actor.user_matrix` — a 4×4 transform evaluated on the GPU —
so moving a robot each frame is a matrix assignment, not a NumPy recompute of the mesh
points. Objects whose geometry genuinely changes each frame (trajectories, glyph
fields) update their points explicitly.

Import them from `ssl_vista.plotters.pv_utils.scene`:

- Foundation: `SceneObject`, `SceneObjectGroup`, `pose_matrix`.
- Primitives: `Mesh`, `Marker`, `PointCloud`, `Line`, `Trajectory`, `StraightLine`,
  `Vector`, `VectorField`, `Icon2D`, `Icon3D`.
- Composites: `Axes`, `Robot2D`, `Robot3D`, `SphereGrid`.

The uniform pose API is `set_pose(position=None, R=None, heading=None)` (NumPy):

```python
robot = self.add_robot("robot_0", "quadrotor", size=0.5, traj_max_len=500)
robot.set_pose(position=p_xyz, R=R_3x3)        # 3D rigid pose
robot.set_traj_points(history_xyz)             # world-frame tail (self-trims)
# 2D:  robot.set_pose(position=p_xy, heading=theta)
```

Add any object to a plotter with `add_scene_object(name, obj)`. A `SceneObjectGroup`
registers each leaf as `"{name}.{child}"`; `follow_pose=True` children move rigidly with
the group, while `follow_pose=False` children (e.g. a world-frame trajectory) are updated
independently.

## Bring your own drawable (no transform code)

Because `SceneObject` already implements pose/attach/style generically, a user object
needs **no transformation functions**. Supply a mesh and it is ready for the plotter:

```python
from ssl_vista.plotters.pv_utils.scene import Mesh
import pyvista as pv

blob = Mesh(pv.Sphere(radius=0.3), color="orange")
self.add_scene_object("blob", blob)
blob.set_pose(position=[3, 0, 0], R=R)     # works out of the box
```

A reusable custom type is just a subclass whose `__init__` builds a mesh; it inherits
`set_pose`, `_attach`, styling, and visibility for free:

```python
class Beacon(SceneObject):
    def __init__(self, height=1.0, **style):
        super().__init__(pv.Cone(height=height, direction=(0, 0, 1)), **style)
```

## Registering built-in plotters

Built-ins are resolved through the plotter registry (`ssl_vista.plotters.registry`).
To make a new built-in available:

1. Add a class under `src/ssl_vista/plotters`.
2. Ensure it inherits from a valid base and exposes required methods.
3. Reference its class name in layout `type`.

The package `plotters/__init__.py` imports classes and registers concrete plotter types at import time.

For local custom plugins, use layout fields `module_path` and `class_name`; these are validated by schema and then loaded by the registry loader.

## Shared context and cross-plotter interaction

`SimulationGridContext` provides shared state/signals.
Current signal:

- `robot_focus_changed`

Use this to synchronize robot selection across plotters.

## Recommended implementation checklist

- Validate required keys/shapes in `init_artists` or custom checks.
- Avoid expensive recomputation in per-frame updates.
- Keep state in instance attributes, not globals.
- Provide sane defaults for label names and style args.
- Document required data keys in docstring.

## Testing custom plotters

- Start with bundled sample data to verify base behavior.
- Exercise keyboard interactions if overridden.
- Confirm layout loading failures are explicit for bad config.
- Run `just test` and `just docs-build` before submitting changes.
