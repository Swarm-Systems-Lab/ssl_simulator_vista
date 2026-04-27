from pathlib import Path
from struct import pack
from typing import Annotated, Optional

import typer
from ssl_simulator.logging import LoggerManager

from ssl_vista.data import DataManager

from .app import run_app

app = typer.Typer(
    context_settings={"help_option_names": ["-h", "--help"]}, pretty_exceptions_show_locals=False
)


@app.command()
def run(
    layout: str | None = typer.Option(
        None,
        "-l",
        "--layout",
        help="Layout type (name from grid_layouts folder) or relative JSON layout file",
    ),
    list_layouts_flag: bool = typer.Option(
        False,
        "-ll",
        "--list-layouts",
        help="Show all available layouts from grid_layouts folder and exit",
    ),
    data: Annotated[
        Path | None,
        typer.Option(
            "-data",
            "--data-path",
            help="Path to CSV data file",
        ),
    ] = None,
    list_data_flag: bool = typer.Option(
        False,
        "-ld",
        "--list-data",
        help="Show all available testing data samples and exit",
    ),
    auto_play: bool = typer.Option(
        False,
        "-ap",
        "--auto-play",
        help="Automatically start the simulation upon loading (data file required)",
    ),
    log_level: str = typer.Option(
        "INFO",
        "-log",
        "--log-level",
        help="Logging level (DEBUG_VERBOSE, DEBUG, INFO, WARNING, ERROR)",
    ),
    log_format: str = typer.Option(
        "compact",
        "-fmt",
        "--log-format",
        help="Logging format (simple, compact, standard, detailed)",
    ),
):
    """
    SSL Simulator Vista - A PyVista/Matplotlib-based Visualization Tool for the SSL Simulator

    This CLI launch the Qt application with given layout and data.

    Examples:
      sslvista -l 2d_canvas -data ./data/my_data.csv
      sslvista -l ./layouts/custom.json -data ./data/my_data.csv
    """

    # --- Init logging based on debug flag ---
    try:
        LoggerManager().setup(
            level=log_level, format_type=log_format, packages=["ssl_vista", "ssl_simulator"]
        )
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from None

    # --- Handle listing layouts and samples ---
    if list_layouts_flag:
        layouts = DataManager.list_available_layouts()
        if not layouts:
            typer.echo("No layouts found in grid_layouts folder.")
        else:
            typer.echo("Available layouts:")
            for name in layouts:
                typer.echo(f"  - {name}")
        raise typer.Exit()

    if list_data_flag:
        samples = DataManager.list_available_samples()
        if not samples:
            typer.echo("No samples found in samples folder.")
        else:
            typer.echo("Available samples:")
            for name in samples:
                typer.echo(f"  - {name}")
        raise typer.Exit()

    # --- Handle layout argument ---
    layout_file = None
    if layout is not None:
        layout_file = DataManager.get_grid_layout_path(layout)

    # --- Handle data argument ---
    data_file = None

    if data is not None:
        data_file = DataManager.get_sample_path(data) if data.suffix != ".csv" else Path(data)
        if not data_file.exists():
            raise typer.BadParameter(f"Data file '{data}' not found.")
    else:
        data_file = None

    # --- Call the main app ---
    run_app(layout=layout_file, data_path=data_file, auto_play=auto_play)


if __name__ == "__main__":
    app()
