import typer
from pathlib import Path

from ssl_vista import CONFIG
from ssl_vista.data import get_grid_layout_path, list_available_layouts
from .app import run_app

app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})

# # Path to the folder containing default layouts
# GRID_LAYOUTS_DIR = Path(__file__).parent / "grid_layouts"

@app.command()
def run(
    l: str = typer.Option(
        None,
        "-l",
        "--layout",
        help="Layout type (name from grid_layouts folder) or relative JSON layout file"
    ),
    list_layouts_flag: bool = typer.Option(
        False,
        "-ll",
        "--list-layouts",
        help="Show all available layouts from grid_layouts folder and exit"
    ),
    data: Path = typer.Option(
        None,
        "-data",
        "--data-path",
        help="Path to CSV data file"
    ),
    auto_play: bool = typer.Option(
        False,
        "-ap",
        "--auto-play", 
        help="Automatically start the simulation upon loading (data file required)"
    ),
    debug: bool = typer.Option(
        False,
        "-dbg",
        "--debug",
        help="Enable debug mode for detailed logging"
    ),
    debug_info: bool = typer.Option(
        False,
        "-dbgi",
        "--debug-info",
        help="Enable debug information display in the application"
    )
):
    """
    SSL Simulator Vista - A PyVista/Matplotlib-based Visualization Tool for the SSL Simulator

    This CLI launch the Qt application with given layout and data.
    
    Examples:
      sslvista run -l 2d_canvas -data ./data/my_data.csv
      sslvista run -l ./layouts/custom.json -data ./data/my_data.csv
    """
    if debug:
        CONFIG["DEBUG"] = debug
    if debug_info:
        CONFIG["DEBUG_INFO"] = debug_info

    # --- Handle listing layouts ---
    if list_layouts_flag:
        layouts = list_available_layouts()
        if not layouts:
            typer.echo("No layouts found in grid_layouts folder.")
        else:
            typer.echo("Available layouts:")
            for name in layouts:
                typer.echo(f"  - {name}")
        raise typer.Exit()
        
    # --- Handle layout argument ---
    layout_file = None
    if l is not None:
        layout_file = get_grid_layout_path(l)

    # --- Handle data argument ---
    # if data is None:
    #     raise typer.BadParameter("Data path must be provided with -data / --data-path")
    if data is not None:
        data_file = Path(data)
        if not data_file.exists():
            raise typer.BadParameter(f"Data file '{data}' not found.")
    else:
        data_file = None
    
    # --- Call the main app ---
    run_app(layout=layout_file, data_path=data_file, auto_play=auto_play)


if __name__ == "__main__":
    app()