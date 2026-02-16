# Usage

This page covers practical use of `ssl_vista`: listing available resources, launching the app, and controlling playback.

## Prerequisites

- Python 3.10+
- GUI environment compatible with Qt (X11/xcb on Linux)
- Simulation CSV files generated for `ssl-simulator`

For local development:

```bash
git clone https://gitea.lyapunov.local/Swarm-Systems-Lab/ssl_simulator_vista
cd ssl_vista
just setup
```

## CLI entrypoint

The project exposes `sslvista`:

```bash
uv run sslvista --help
```

Primary options:

- `--layout` / `-l`: layout name (`2d_canvas`) or path to a layout JSON file
- `--data-path` / `-data`: sample name (`data_uny_test`) or CSV path
- `--list-layouts` / `-ll`: print built-in layout names and exit
- `--list-data` / `-ld`: print bundled sample data names and exit
- `--auto-play` / `-ap`: start playback automatically after data load
- `--debug` / `-dbg`: enable debug mode
- `--debug-info` / `-dbgi`: enable verbose simulator data info

## Typical workflows

### 1) Discover bundled resources

```bash
uv run sslvista --list-layouts
uv run sslvista --list-data
```

### 2) Run with bundled layout and sample data

```bash
uv run sslvista --layout 2d_canvas --data-path data_uny_test
uv run sslvista --layout 3d_canvas --data-path data_3d_test
```

### 3) Run with custom files

```bash
uv run sslvista --layout ./my_layout.json --data-path ./my_run.csv
```

### 4) Start immediately playing

```bash
uv run sslvista --layout 3d_canvas --data-path data_3d_test --auto-play
```

## In-app controls

### Toolbar actions

- **Load Grid Layout**: open a JSON layout file
- **Load CSV**: open a simulation CSV file
- **Reload CSV**: reprocess currently loaded file
- **Play / Stop / Reset**: playback controls
- **Time slider**: manual frame selection

### Keyboard shortcuts (main window)

- `Space`: play/pause
- `R`: reset simulation
- `Left` / `Right`: coarse step backward/forward
- `,` / `.`: single-step backward/forward
- `Q`: quit application

### Keyboard shortcuts (3D attitude plotter)

- `PageUp` / `PageDown`: cycle focused robot index
- `R`: reset camera in the attitude panel

## Layout and data inputs

- Layout files are JSON configurations loaded by `SimulationGrid`.
- Each plotter declares required simulation keys and shapes.
- Bundled examples are in `src/ssl_vista/data/grid_layouts` and `src/ssl_vista/data/samples`.

See [Layout schema](layout-schema.md) and [Data schema](data-schema.md) for exact contracts.

## Common dev commands

```bash
just test
just test-fast
just lint
just typecheck
just docs
just docs-build
```

For full command reference, see [Golden path](golden-path.md).

| `just clean` | Remove build artifacts |

### Quick Tips

- 🔧 **List all commands**: `just --list` or `just`
- 🧪 **Run single test**: `just test-one <test_name>`
- 🔍 **Verbose pytest**: `uv run pytest -vv`
- 🐛 **Debug test**: `uv run pytest --pdb`
- ⚡ **Parallel tests**: `uv run pytest -n auto`
- 🔄 **Re-run failed**: `uv run pytest --lf`
