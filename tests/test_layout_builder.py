"""Tests for the public, dependency-light layout builder (``ssl_vista.layout``)."""

import json

import pytest

from ssl_vista.layout import GridLayoutConfig, LayoutBuilder, parse_layout_config


def test_builder_builds_validated_config():
    layout = (
        LayoutBuilder(shape=(2, 1))
        .add_canvas_2d((0, 0), robot={"type": "unicycle", "color": "royalblue"})
        .add_mpl((1, 0), module_path="my_plotter.py", class_name="MyPlotter")
        .build()
    )

    assert isinstance(layout, GridLayoutConfig)
    assert layout.shape == (2, 1)
    assert layout.plotters[0].type == "Plotter2DCanvas"
    assert layout.plotters[0].args == {"robot": {"type": "unicycle", "color": "royalblue"}}
    assert layout.plotters[1].module_path == "my_plotter.py"


def test_builder_output_reparses_through_viewer_loader():
    layout = (
        LayoutBuilder(shape=(1, 1))
        .add_canvas_2d((0, 0), robot={"type": "single_integrator"})
        .build()
    )

    # A layout produced by the builder must be schema-valid for the viewer.
    reparsed = parse_layout_config(json.loads(layout.to_json()))
    assert reparsed == layout


def test_builder_rejects_out_of_bounds_position():
    with pytest.raises(ValueError, match="out of bounds"):
        LayoutBuilder(shape=(1, 1)).add_canvas_2d((0, 1)).build()


def test_builder_rejects_duplicate_positions():
    with pytest.raises(ValueError, match="Duplicate plotter position"):
        (LayoutBuilder(shape=(2, 2)).add_canvas_2d((0, 0)).add_canvas_3d((0, 0)).build())


def test_canvas_args_omit_unset_namespaces():
    layout = LayoutBuilder(shape=(1, 1)).add_canvas_2d((0, 0), grid={"range": 5}).build()
    # Only the namespaces the caller supplied should appear.
    assert layout.plotters[0].args == {"grid": {"range": 5}}


def test_optional_robot_type_check_rejects_unknown_type():
    builder = LayoutBuilder(shape=(1, 1)).add_canvas_2d((0, 0), robot={"type": "spaceship"})
    # Off by default (dependency-light); opt-in validates against RobotFactory.
    builder.build()  # no raise
    with pytest.raises(ValueError, match="Unknown 2D robot type"):
        builder.build(check_robot_types=True)
