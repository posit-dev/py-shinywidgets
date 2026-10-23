import ipywidgets
import matplotlib
import pandas as pd
import panel as pn
import param
import plotly.graph_objects as go
import pytest
from jupyter_bokeh import BokehModel
from matplotlib.figure import Figure
from shiny import Session
from shiny.session import session_context
from shinywidgets import as_widget, render_panel

matplotlib.use("agg")


class Dashboard(pn.viewable.Viewer):
    value = param.Integer(default=1)

    def __panel__(self) -> pn.viewable.Viewable:
        return pn.Column(pn.widgets.IntSlider.from_param(self.param.value))


class Counter(pn.custom.JSComponent):
    count = param.Integer(default=0)
    _esm = "export function render({ model }) { return document.createElement('div') }"


class FancySlider(pn.widgets.IntSlider):
    pass


@pytest.mark.parametrize(
    "make", [Dashboard, Counter, FancySlider], ids=["Viewer", "JSComponent", "widget"]
)
def test_as_widget_coerces_user_defined_panel_subclasses(
    widget_session: Session, make: type
) -> None:
    with session_context(widget_session):
        assert isinstance(as_widget(make()), BokehModel)


@pytest.mark.parametrize(
    "make",
    [
        lambda: "# Some markdown",
        lambda: pd.DataFrame({"x": [1, 2, 3]}),
        lambda: Figure(),
        lambda: go.Figure(go.Scatter(x=[1, 2], y=[1, 2])),
        lambda: Dashboard(),
    ],
    ids=["str", "DataFrame", "matplotlib", "plotly", "Viewer"],
)
def test_render_panel_routes_values_through_pn_panel(
    widget_session: Session, make
) -> None:
    with session_context(widget_session):
        assert isinstance(render_panel()._as_widget(make()), BokehModel)


def test_render_panel_passes_widgets_through(widget_session: Session) -> None:
    with session_context(widget_session):
        w = ipywidgets.IntSlider()
        assert render_panel()._as_widget(w) is w
