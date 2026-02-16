from pathlib import Path

import pytest

from ssl_vista.ui.layout_schema import LayoutSchemaError, parse_layout_config


def test_parse_layout_config_minimal_defaults():
    config = parse_layout_config({})

    assert config.shape == (1, 1)
    assert config.plotters == []


def test_parse_layout_config_rejects_out_of_bounds_position():
    with pytest.raises(LayoutSchemaError, match="out of bounds"):
        parse_layout_config(
            {
                "shape": [1, 1],
                "plotters": [
                    {
                        "type": "Plotter2DCanvas",
                        "position": [0, 1],
                    }
                ],
            }
        )


def test_parse_layout_config_rejects_duplicate_positions():
    with pytest.raises(LayoutSchemaError, match="Duplicate plotter position"):
        parse_layout_config(
            {
                "shape": [2, 2],
                "plotters": [
                    {"type": "Plotter2DCanvas", "position": [0, 0]},
                    {"type": "Plotter3DCanvas", "position": [0, 0]},
                ],
            }
        )


def test_parse_layout_config_rejects_base_mpl_without_loader_fields():
    with pytest.raises(LayoutSchemaError, match="requires both 'module_path' and 'class_name'"):
        parse_layout_config(
            {
                "shape": [1, 1],
                "plotters": [
                    {
                        "type": "BaseMplPlotter",
                        "position": [0, 0],
                    }
                ],
            }
        )


def test_parse_layout_config_accepts_custom_plotter_loader_fields():
    config = parse_layout_config(
        {
            "shape": [2, 2],
            "plotters": [
                {
                    "type": "BaseMplPlotter",
                    "position": [1, 1],
                    "module_path": "mpl_example.py",
                    "class_name": "PlotterMplExample",
                    "args": {"figsize": [6, 4]},
                }
            ],
        },
        source=Path("example_mpl.json"),
    )

    assert config.plotters[0].module_path == "mpl_example.py"
    assert config.plotters[0].class_name == "PlotterMplExample"
    assert config.plotters[0].position == (1, 1)
