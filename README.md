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

If you want to use this package in a project, you can add the following line to your `requirements.txt` file:

```
git+https://github.com/Swarm-Systems-Lab/ssl_simulator_vista.git
```

> ⚠️ All dependencies, including the simulator and PyVista, are specified in `pyproject.toml` to ensure compatibility. Do **not modify dependency versions** to guarantee stable and reproducible environments.

## Usage

You can launch the application from anywhere once the virtual environment is active:

```bash
sslvista
```

### Options:

- `-l` / `--layout` : Layout type (name from `grid_layouts` folder) or relative path to a `.json` layout file.
- `-ll` / `--list-layouts` : Show all available layouts from the `grid_layouts` folder and exit.
- `-data` / `--data-path` : Path to a CSV data file (or sample name from the `samples` folder).
- `-ld` / `--list-data` : Show all available testing data samples and exit.
- `-ap` / `--auto-play` : Automatically start the simulation upon loading (data file required).
- `-dbg` / `--debug` : Enable debug mode for detailed logging.
- `-dbgi` / `--debug-info` : Enable debug information display in the application.

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
