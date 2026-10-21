import subprocess
import sys
import typing

import pytest


def test_plotly_config_alias() -> None:
    from shinywidgets.types import PlotlyConfig

    assert typing.get_origin(PlotlyConfig) is dict
    assert typing.get_args(PlotlyConfig) == (str, typing.Any)


def test_plotly_figure_alias() -> None:
    pytest.importorskip("plotly")
    import plotly.graph_objects as go
    from ipywidgets import Widget
    from shinywidgets.types import PlotlyFigure

    # A PlotlyFigure is a raw figure or a pre-built widget (sibling classes)
    assert set(typing.get_args(PlotlyFigure)) == {go.Figure, go.FigureWidget}
    assert not issubclass(go.FigureWidget, go.Figure)
    assert issubclass(go.FigureWidget, Widget)


def test_plotly_value_alias() -> None:
    pytest.importorskip("plotly")
    from ipywidgets import Widget
    from shinywidgets.types import PlotlyConfig, PlotlyFigure, PlotlyValue

    # A PlotlyValue is a PlotlyFigure, optionally paired with a config as a
    # (figure, config) tuple, or any ipywidgets.Widget
    *figure_args, tuple_of, widget = typing.get_args(PlotlyValue)
    assert set(figure_args) == set(typing.get_args(PlotlyFigure))
    inner_figure, config = typing.get_args(tuple_of)
    assert set(typing.get_args(inner_figure)) == set(typing.get_args(PlotlyFigure))
    assert config == PlotlyConfig
    assert widget is Widget


def test_types_module_is_exposed() -> None:
    import shinywidgets

    assert shinywidgets.types.__name__ == "shinywidgets.types"


def test_unknown_attribute_still_raises() -> None:
    import shinywidgets.types

    with pytest.raises(AttributeError, match="no attribute"):
        shinywidgets.types.NotARealName  # noqa: B018


def test_aliases_are_lazy_when_plotly_missing() -> None:
    # Block plotly and verify that shinywidgets still imports, PlotlyConfig
    # (the only eager alias) still works, and the lazy aliases raise a
    # helpful ImportError.
    script = """
import sys
sys.modules["plotly"] = None
sys.modules["plotly.graph_objects"] = None

import shinywidgets
from shinywidgets.types import PlotlyConfig  # noqa: F401

for name in ("PlotlyFigure", "PlotlyValue"):
    try:
        getattr(shinywidgets.types, name)
    except ImportError as e:
        assert name in str(e), str(e)
    else:
        raise AssertionError(f"expected ImportError for {name}")
"""
    subprocess.run([sys.executable, "-c", script], check=True)
