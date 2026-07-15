"""Tests for the canvas plotter configuration models."""

import pytest
from pydantic import ValidationError

from ssl_vista.plotters.pv_utils.configs import (
    DEFAULT_GRAPHICS,
    CameraConfig,
    GraphicsConfig,
    GridConfig,
    RobotConfig,
)


def test_grid_defaults_and_style_keys():
    cfg = GridConfig()
    assert cfg.range is None and cfg.ticks is None
    style = cfg.show_bounds_style()
    assert set(style) == {
        "font_size",
        "xtitle",
        "ytitle",
        "ztitle",
        "bold",
        "color",
        "grid",
        "minor_ticks",
    }
    assert style["font_size"] == 15 and style["color"] == "black"


def test_extra_forbid_rejects_typos():
    with pytest.raises(ValidationError):
        GridConfig(fnt_size=12)
    with pytest.raises(ValidationError):
        CameraConfig(bg="black")


def test_build_accepts_none_dict_instance_with_defaults():
    # None -> defaults
    assert GridConfig.build(None, range=2).range == 2
    # dict overrides defaults key-by-key
    assert GridConfig.build({"range": 3}, range=2, ticks=7).range == 3
    assert GridConfig.build({"range": 3}, ticks=7).ticks == 7
    # instance returned unchanged (defaults ignored)
    inst = GridConfig(range=9)
    assert GridConfig.build(inst, range=2) is inst


def test_camera_resolved_per_dimension():
    r2 = CameraConfig().resolved(2)
    assert r2["position"] == "xy" and r2["parallel"] is True and r2["lights"] == "2d"
    r3 = CameraConfig().resolved(3)
    assert r3["position"] == "iso" and r3["parallel"] is False and r3["lights"] == "three"
    # explicit overrides win; azimuth passes through
    r = CameraConfig(position="yz", parallel=False, azimuth=-80).resolved(2)
    assert r["position"] == "yz" and r["parallel"] is False and r["azimuth"] == -80


def test_robot_resolve_merges_flat_aliases():
    defaults = {"type": "unicycle", "color": "darkgrey", "size": 0.5}
    # flat alias fills a field; None aliases are ignored
    cfg = RobotConfig.resolve(None, defaults=defaults, color="red", size=None)
    assert cfg.color == "red" and cfg.size == 0.5 and cfg.type == "unicycle"
    # namespace beats flat alias for the same key
    cfg = RobotConfig.resolve({"color": "green"}, defaults=defaults, color="red")
    assert cfg.color == "green"
    # instance passthrough
    inst = RobotConfig(color="cyan")
    assert RobotConfig.resolve(inst, defaults=defaults, color="red") is inst


def test_graphics_defaults():
    assert DEFAULT_GRAPHICS.trajectory_size == 4.0
    assert GraphicsConfig(trajectory_size=10).trajectory_size == 10
