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
      "args": {"robot_type": "unicycle", "robot_color": "blue"}
    }
  ]
}
```

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
      "args": {"robot_type": "unicycle", "robot_color": "blue"}
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
