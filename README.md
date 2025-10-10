# SSL Simulator Visualizer

## Installation

We recommend creating a dedicated virtual environment to avoid conflicts with other Python packages:

```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows
```

Then, install the package in editable mode to allow development changes:

```bash
pip install --upgrade pip
pip install -e .
```

Installing with `-e` (editable) ensures that any changes to the source code are reflected immediately without reinstalling.

> ⚠️ All dependencies, including the simulator and PyVista, are specified in `pyproject.toml` to ensure compatibility. Do **not modify dependency versions** to guarantee stable and reproducible environments.

## Usage

You can launch the application from anywhere once the virtual environment is active:

```bash
sslvista
```

### Options:
- `-l` / `--layout` : Name of a layout in `grid_layouts` or a relative path to a `.json` layout file.
- `-data` / `--data-path` : Relative path to the CSV data file.
- `--list-layouts` : Show all available layouts in `grid_layouts` and exit.
- `-ap` / `--auto-play` : Automatically start the simulation once the data file is loaded.
- `-h` / `--help` : Show the help message.

### Example:

```bash
# List available layouts
sslvista -ll

# Use a default 3D layout (providing -data is optional)
sslvista -l 3d_canvas -data ./data/my_simulation.csv -ap

# Use a custom layout file
sslvista -l ./layouts/custom_layout.json -data ./data/my_simulation.csv
```

## Credits

- **[Jesús Bautista Villar](https://sites.google.com/view/jbautista-research)** (<jesbauti20@gmail.com>) – Main Developer
