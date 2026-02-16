# Data schema

`ssl_vista` receives simulation data by calling `ssl_simulator.load_sim(csv_path)`.
The returned `sim_data` dictionary must contain keys and array shapes expected by each active plotter.

## Common key

- `time`: array with time values of shape `(T,)`

## Plotter-specific requirements

## `Plotter2DCanvas`

Default labels:

- position key: `robot.p`
- heading key: `robot.theta`

Expected shapes:

- `robot.p`: `(T, N, 2)`
- `robot.theta`: `(T, N)`

Notes:

- Heading key can be `None` only if configured that way in plotter args.
- Position must always exist.

## `Plotter3DCanvas`

Default labels:

- position key: `robot.p`
- rotation key: `robot.R`

Expected shapes:

- `robot.p`: `(T, N, 3)`
- `robot.R`: `(T, N, 3, 3)`

Notes:

- Rotation key can be `None` only if configured that way in args.
- Position must always exist.

## `Plotter3DAttitude`

Default label:

- rotation key: `robot.R`

Expected shape:

- `robot.R`: `(T, N, 3, 3)`

This plotter rotates a local axis triad for the selected robot index.

## Examples

Bundled samples:

- `src/ssl_vista/data/samples/data_uny_test.csv`
- `src/ssl_vista/data/samples/data_3d_test.csv`

Use CLI names:

```bash
uv run sslvista --layout 2d_canvas --data-path data_uny_test
uv run sslvista --layout 3d_canvas --data-path data_3d_test
```

## Diagnosing schema mismatches

If you see shape/key errors:

1. Verify the chosen layout plotter types.
2. Check plotter label overrides in layout `args`.
3. Validate arrays emitted by `ssl_simulator.load_sim`.
4. Compare against bundled sample files and this page.
