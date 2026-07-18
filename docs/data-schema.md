# Data schema

`ssl_vista` receives simulation data by calling `ssl_simulator.load_sim(csv_path)`.
The returned `sim_data` dictionary must contain keys and array shapes expected by each active plotter.

Lookup is by **exact key**. `ssl_simulator` logs **flat** component names (`p`, `theta`, `R`) with no
`robot.`/`ctrl.` prefix, and the plotter defaults below match that. Any label can be overridden per
plotter in the layout's `args`.

## Common key

- `time`: array with time values of shape `(T,)`

## Plotter-specific requirements

## `Plotter2DCanvas`

Default labels:

- position key (`label_pos`): `p`
- heading key (`label_heading`): `theta`

Expected shapes:

- `p`: `(T, N, 2)`
- `theta`: `(T, N)`

Notes:

- Position must always exist.
- The heading is only required for *directional* robot types (e.g. `unicycle`). Symmetric types
  such as `single_integrator` are drawn from position alone and ignore it.

## `Plotter3DCanvas`

Default labels:

- position key (`label_pos`): `p`
- rotation key (`label_rot`): `R`

Expected shapes:

- `p`: `(T, N, 3)`
- `R`: `(T, N, 3, 3)`

Notes:

- Position must always exist.
- As in 2D, the rotation is only required for directional robot types.

## `Plotter3DAttitude`

Default label:

- rotation key (`label_rot`): `R`

Expected shape:

- `R`: `(T, N, 3, 3)`

This plotter rotates a local axis triad for the selected robot index.

## Overriding the labels

If your run logs different names, point the plotter at them in the layout `args`:

```json
{
  "type": "Plotter3DCanvas",
  "position": [0, 0],
  "args": {"label_pos": "p_est", "label_rot": "R_body"}
}
```

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
3. Validate arrays emitted by `ssl_simulator.load_sim` - print `list(sim_data)` to see the exact
   keys your run produced.
4. Compare against bundled sample files and this page.
