import subprocess
import sys
import typing

import pytest

LAZY_ALIASES = [
    "AltairValue",
    "BokehValue",
    "HoloviewsValue",
    "MaplibreValue",
    "PanelValue",
    "PlotlyFigure",
    "PlotlyValue",
    "PydeckValue",
]


def test_plotly_config_alias() -> None:
    from shinywidgets.types import PlotlyConfig

    assert typing.get_origin(PlotlyConfig) is dict
    assert typing.get_args(PlotlyConfig) == (str, typing.Any)


def test_plotly_figure_alias() -> None:
    pytest.importorskip("plotly")
    import plotly.graph_objects as go
    from ipywidgets import Widget
    from shinywidgets.types import PlotlyConfig, PlotlyFigure, PlotlyValue

    # A PlotlyFigure is a raw figure or a pre-built widget (sibling classes)
    assert set(typing.get_args(PlotlyFigure)) == {go.Figure, go.FigureWidget}
    assert not issubclass(go.FigureWidget, go.Figure)
    assert issubclass(go.FigureWidget, Widget)

    # A PlotlyValue is a PlotlyFigure, optionally paired with a config as a
    # (figure, config) tuple, or any ipywidgets.Widget
    *figure_args, tuple_of, widget = typing.get_args(PlotlyValue)
    assert set(figure_args) == set(typing.get_args(PlotlyFigure))
    inner_figure, config = typing.get_args(tuple_of)
    assert set(typing.get_args(inner_figure)) == set(typing.get_args(PlotlyFigure))
    assert config == PlotlyConfig
    assert widget is Widget


def test_altair_value_alias() -> None:
    pytest.importorskip("altair")
    import altair as alt
    from shinywidgets.types import AltairValue

    top_level, widget = typing.get_args(AltairValue)
    assert issubclass(alt.Chart, top_level)
    assert issubclass(alt.ConcatChart, top_level)
    assert issubclass(alt.JupyterChart, widget)


def test_bokeh_value_alias() -> None:
    pytest.importorskip("bokeh")
    from bokeh.models import LayoutDOM
    from bokeh.plotting import figure
    from ipywidgets import Widget
    from shinywidgets.types import BokehValue

    assert typing.get_args(BokehValue) == (LayoutDOM, Widget)
    assert isinstance(figure(), BokehValue)


def test_holoviews_value_alias() -> None:
    pytest.importorskip("holoviews")
    import holoviews as hv
    from holoviews.core.dimension import Dimensioned
    from ipywidgets import Widget
    from shinywidgets.types import HoloviewsValue

    assert typing.get_args(HoloviewsValue) == (Dimensioned, Widget)
    assert isinstance(hv.Curve([1, 2, 3]), HoloviewsValue)


def test_maplibre_value_alias() -> None:
    pytest.importorskip("maplibre")
    from ipywidgets import Widget
    from maplibre.map import Map
    from shinywidgets.types import MaplibreValue

    assert typing.get_args(MaplibreValue) == (Map, Widget)


def test_panel_value_alias() -> None:
    pytest.importorskip("panel")
    from ipywidgets import Widget
    from panel.viewable import Viewable
    from shinywidgets.types import PanelValue

    assert typing.get_args(PanelValue) == (Viewable, Widget)


def test_pydeck_value_alias() -> None:
    pytest.importorskip("pydeck")
    import pydeck
    from ipywidgets import Widget
    from shinywidgets.types import PydeckValue

    assert typing.get_args(PydeckValue) == (pydeck.Deck, Widget)


@pytest.mark.parametrize("name", LAZY_ALIASES)
def test_aliases_resolve(name: str) -> None:
    import shinywidgets.types

    assert getattr(shinywidgets.types, name) is not None


def test_types_module_is_exposed() -> None:
    import shinywidgets

    assert shinywidgets.types.__name__ == "shinywidgets.types"


def test_unknown_attribute_still_raises() -> None:
    import shinywidgets.types

    with pytest.raises(AttributeError, match="no attribute"):
        shinywidgets.types.NotARealName  # noqa: B018


def test_aliases_are_lazy_when_optional_deps_missing() -> None:
    # Block every optional dependency and verify that shinywidgets still
    # imports, PlotlyConfig (the only eager alias) still works, and lazy
    # aliases raise a helpful ImportError.
    pkgs = [
        "altair",
        "bokeh",
        "holoviews",
        "hvplot",
        "jupyter_bokeh",
        "maplibre",
        "panel",
        "plotly",
        "pydeck",
    ]
    script = f"""
import sys
for pkg in {pkgs!r}:
    sys.modules[pkg] = None

import shinywidgets
from shinywidgets.types import PlotlyConfig  # noqa: F401

for name in {LAZY_ALIASES!r}:
    try:
        getattr(shinywidgets.types, name)
    except ImportError as e:
        assert name in str(e), str(e)
    else:
        raise AssertionError(f"expected ImportError for {{name}}")
"""
    subprocess.run([sys.executable, "-c", script], check=True)
