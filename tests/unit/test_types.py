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
    from shinywidgets.types import PlotlyFigure

    figure, tuple_of = typing.get_args(PlotlyFigure)
    assert figure is go.Figure
    assert typing.get_args(tuple_of)[0] is go.Figure


def test_types_module_is_exposed() -> None:
    import shinywidgets

    assert shinywidgets.types.__name__ == "shinywidgets.types"


def test_unknown_attribute_still_raises() -> None:
    import shinywidgets.types

    with pytest.raises(AttributeError, match="no attribute"):
        shinywidgets.types.NotARealName  # noqa: B018


def test_aliases_are_lazy_when_plotly_missing() -> None:
    # Block plotly and verify that shinywidgets still imports, PlotlyConfig
    # (the only eager alias) still works, and PlotlyFigure raises a helpful
    # ImportError.
    script = """
import sys
sys.modules["plotly"] = None
sys.modules["plotly.graph_objects"] = None

import shinywidgets
from shinywidgets.types import PlotlyConfig  # noqa: F401

try:
    shinywidgets.types.PlotlyFigure
except ImportError as e:
    assert "PlotlyFigure" in str(e), str(e)
else:
    raise AssertionError("expected ImportError")
"""
    subprocess.run([sys.executable, "-c", script], check=True)
