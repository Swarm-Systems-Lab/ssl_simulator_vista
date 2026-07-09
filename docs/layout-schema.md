# Layout schema

Grid layouts are JSON files consumed by `load_grid_from_json` (`src/ssl_vista/ui/grid.py`).
They are validated against strict Pydantic models before any Qt widgets or plotters are created.

## Top-level schema

```json
{
  "shape": [rows, cols],
  "plotters": [
    {
      "type": "Plotter2DCanvas",
      "position": [0, 0],
      "args": {
        "robot": {"type": "unicycle", "color": "blue"},
        "grid": {"range": 5, "ticks": 11, "font_size": 12},
        "camera": {"background": "white"}
      }
    }
  ]
}
```

### Config namespaces in `args`

Canvas-plotter options are grouped into typed **namespaces**, each forwarded whole to its
sub-component (so any option a sub-component supports is reachable from a layout):

- `grid` — grid range/ticks and label style (`range`, `ticks`, `font_size`, `xtitle`,
  `ytitle`, `ztitle`, `bold`, `color`, `grid`, `minor_ticks`).
- `camera` — `background`, `position`, `parallel`, `lights` (`"three"|"2d"`), `azimuth`.
  Unset fields resolve to per-dimension defaults.
- `robot` — `type`, `color`, `size`, `tail`, `axes`.
- `graphics` — default line sizes (`axes_line_width`, `trajectory_size`, ...).

Each namespace is validated (`extra="forbid"`), so a typo like `{"grid": {"fnt_size": 12}}`
raises instead of being silently ignored. The flat `robot_*` args
(`robot_type`, `robot_color`, `robot_size`, `robot_tail`, `robot_axes`) still work but are
**deprecated** in favor of the `robot` namespace.

Fields:

- `shape` (optional): two integers `[rows, cols]`; default `[1, 1]`
- `plotters` (optional): list of plotter entries; default `[]`

## Plotter entry fields

- `type` (optional, default `Plotter2DCanvas`)
- `position` (optional, default `[0, 0]`)
- `args` (optional, default `{}`)
- `module_path` (required only for dynamic custom plotter loading)
- `class_name` (required only for dynamic custom plotter loading)

## Built-in plotters

Use a concrete built-in class name for `type`:

- `Plotter2DCanvas`
- `Plotter3DCanvas`
- `Plotter3DAttitude`

Example (`2d_canvas.json`):

```json
{
  "shape": [1, 1],
  "plotters": [
    {
      "type": "Plotter2DCanvas",
      "position": [0, 0],
      "args": {
        "robot": {"type": "unicycle", "color": "blue"},
        "grid": {"range": 5, "ticks": 11}
      }
    }
  ]
}
```

## Dynamic custom Matplotlib plotter loading

A dynamic plotter entry uses:

- `type`: a `Base...` selector path in current loader behavior
- `module_path`: Python file to load from
- `class_name`: class defined in that file

Example (`example_mpl.json`):

```json
{
  "shape": [2, 2],
  "plotters": [
    {
      "type": "BaseMplPlotter",
      "position": [0, 1],
      "module_path": "mpl_example.py",
      "class_name": "PlotterMplExample"
    }
  ]
}
```

`module_path` is resolved relative to the layout JSON file path.

## Validation behavior

Validation is strict (`extra="forbid"`) and enforces:

- position bounds inside `shape`
- one plotter per grid cell
- `module_path` + `class_name` required together
- `module_path` + `class_name` required for custom dynamic entries

After schema validation, plotter classes are resolved through the plotter registry.

Errors raise schema validation exceptions (invalid layout shape/fields/positions) or loader exceptions (missing file, unknown class/type).
