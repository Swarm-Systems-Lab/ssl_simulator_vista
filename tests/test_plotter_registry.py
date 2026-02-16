import os
from textwrap import dedent
from typing import Protocol, cast

import pytest

import ssl_vista.plotters as plotters
from ssl_vista.plotters._base_plotters import _BasePlotter
from ssl_vista.plotters.registry import create_plotter_instance, get_plotter_class


class _DummyPlotterProtocol(Protocol):
    context: dict[str, str]
    kwargs: dict[str, str]


@pytest.mark.skipif(
    not os.environ.get("DISPLAY") and os.environ.get("CI") == "true",
    reason="Skipping GUI imports in headless CI environment",
)
def test_get_plotter_class_returns_registered_builtin():
    cls = get_plotter_class("Plotter2DCanvas")

    assert cls.__name__ == "Plotter2DCanvas"


def test_get_plotter_class_rejects_unknown_type():
    with pytest.raises(ValueError, match="Unknown plotter type"):
        get_plotter_class("DoesNotExistPlotter")


def test_create_plotter_instance_loads_local_plugin(tmp_path):
    plugin_file = tmp_path / "plugin_plotter.py"
    plugin_file.write_text(
        dedent(
            """
            from ssl_vista.plotters._base_plotters import _BasePlotter


            class DummyPlotter(_BasePlotter):
                def __init__(self, context=None, **kwargs):
                    super().__init__(**kwargs)
                    self.context = context
                    self.kwargs = kwargs

                def setup_scene(self):
                    pass

                def reset_scene(self, sim_data, sim_settings):
                    pass

                def update_all_scene_objects(self, sim_data, idx):
                    pass
            """
        ),
        encoding="utf-8",
    )

    instance = create_plotter_instance(
        "BaseMplPlotter",
        context={"source": "test"},
        module_path=str(plugin_file),
        class_name="DummyPlotter",
        foo="bar",
    )
    dummy = cast(_DummyPlotterProtocol, instance)

    assert isinstance(instance, _BasePlotter)
    assert dummy.context == {"source": "test"}
    assert dummy.kwargs["foo"] == "bar"


def test_create_plotter_instance_rejects_non_plotter_plugin(tmp_path):
    plugin_file = tmp_path / "bad_plugin.py"
    plugin_file.write_text(
        dedent(
            """
            class BadPlotter:
                pass
            """
        ),
        encoding="utf-8",
    )

    with pytest.raises(TypeError, match="must inherit from _BasePlotter"):
        create_plotter_instance(
            "BaseMplPlotter",
            module_path=str(plugin_file),
            class_name="BadPlotter",
        )
