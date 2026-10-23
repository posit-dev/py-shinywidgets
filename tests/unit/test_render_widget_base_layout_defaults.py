from typing import TYPE_CHECKING

import pytest
import shinywidgets._render_widget_base as rwb

if TYPE_CHECKING:
    from jscatter import Scatter


class StubSession:
    def is_stub_session(self) -> bool:
        return True


@pytest.fixture(autouse=True)
def _stub_widget_construction_session(monkeypatch):
    # If shinywidgets._shinywidgets has been imported anywhere (including other unit
    # tests), ipywidgets will call init_shiny_widget() on widget construction. Patch
    # it to see a stub session and no-op.
    import shinywidgets._shinywidgets as sw

    monkeypatch.setattr(sw, "get_current_session", lambda: StubSession())


def test_non_domwidget_is_returned_unchanged_and_fill_true() -> None:
    dummy = object()
    widget, fill = rwb.set_layout_defaults(dummy)  # type: ignore[arg-type]
    assert widget is dummy
    assert fill is True


def test_controls_widgets_do_not_fill() -> None:
    import ipywidgets as widgets

    w = widgets.IntSlider()
    _, fill = rwb.set_layout_defaults(w)
    assert fill is False


def test_layout_height_non_auto_disables_fill() -> None:
    import ipywidgets as widgets

    w = widgets.Output(layout=widgets.Layout(height="200px"))
    _, fill = rwb.set_layout_defaults(w)
    assert fill is False


def test_layout_height_auto_keeps_fill_true() -> None:
    import ipywidgets as widgets

    w = widgets.Output(layout=widgets.Layout(height="auto"))
    _, fill = rwb.set_layout_defaults(w)
    assert fill is True


def test_plotly_layout_height_disables_fill_and_normalizes_margins(monkeypatch) -> None:
    pytest.importorskip("plotly")
    import plotly.graph_objects as go

    # Force the plotly branch regardless of widget_pkg() heuristics.
    monkeypatch.setattr(rwb, "widget_pkg", lambda _widget: "plotly")

    w = go.FigureWidget()

    # Make expectations stable across plotly versions.
    w._config = {}  # type: ignore[attr-defined]
    w.layout.height = 400
    w.layout.margin.t = 60

    update_layout_calls = []

    def _spy_update_layout(layout):  # type: ignore[no-untyped-def]
        update_layout_calls.append(layout)

    monkeypatch.setattr(w, "update_layout", _spy_update_layout)

    _, fill = rwb.set_layout_defaults(w)
    assert fill is False
    assert w.layout.margin.t == 32
    assert update_layout_calls and update_layout_calls[0] is w.layout


def test_plotly_when_fill_true_sets_responsive_config(monkeypatch) -> None:
    pytest.importorskip("plotly")
    import plotly.graph_objects as go

    monkeypatch.setattr(rwb, "widget_pkg", lambda _widget: "plotly")

    w = go.FigureWidget()
    w._config = {}  # type: ignore[attr-defined]
    w.layout.height = None

    _, fill = rwb.set_layout_defaults(w)
    assert fill is True
    assert w._config.get("responsive") is True  # type: ignore[attr-defined]


def test_altair_sets_container_width_height(monkeypatch) -> None:
    alt = pytest.importorskip("altair")

    monkeypatch.setattr(rwb, "widget_pkg", lambda _widget: "altair")

    chart = (
        alt.Chart(alt.Data(values=[{"x": 1, "y": 2}]))
        .mark_point()
        .encode(x="x:Q", y="y:Q")
    )
    w = alt.JupyterChart(chart)

    _, fill = rwb.set_layout_defaults(w)
    assert fill is True

    assert w.spec.get("width") == "container"
    assert w.spec.get("height") == "container"


def test_altair_keeps_user_defined_size(monkeypatch) -> None:
    alt = pytest.importorskip("altair")

    monkeypatch.setattr(rwb, "widget_pkg", lambda _widget: "altair")

    chart = (
        alt.Chart(alt.Data(values=[{"x": 1, "y": 2}]))
        .mark_point()
        .encode(x="x:Q", y="y:Q")
        .properties(height=200)
    )
    w = alt.JupyterChart(chart)

    rwb.set_layout_defaults(w)

    assert w.spec.get("width") == "container"
    assert w.spec.get("height") == 200


def test_altair_preserves_selection_and_param_observers(monkeypatch) -> None:
    # Altair documents observing a JupyterChart's selections/params before display
    # (jchart.selections.observe(cb, ["brush"])); layout defaults must not orphan them.
    alt = pytest.importorskip("altair")

    monkeypatch.setattr(rwb, "widget_pkg", lambda _widget: "altair")

    brush = alt.selection_interval(name="brush")
    size = alt.param(name="size", value=10)
    chart = (
        alt.Chart(alt.Data(values=[{"x": 1, "y": 2}]))
        .mark_point()
        .encode(x="x:Q", y="y:Q")
        .add_params(brush, size)
    )
    w = alt.JupyterChart(chart)
    seen: list[str] = []
    w.selections.observe(lambda change: seen.append(change["name"]), ["brush"])
    w.params.observe(lambda change: seen.append(change["name"]), ["size"])

    rwb.set_layout_defaults(w)

    assert w.spec.get("width") == "container"
    w._vl_selections = {"brush": {"value": {"x": [0, 1]}, "store": []}}
    w._params = {"size": 20}
    assert seen == ["brush", "size"]


def test_altair_vegafusion_pending_spec_falls_back_to_chart(monkeypatch) -> None:
    # A JupyterChart constructed inside `with alt.data_transformers.enable(
    # "vegafusion"):` keeps `.spec` as None until the browser reports its timezone.
    # Layout defaults run after that context exits, so the active transformer is no
    # longer "vegafusion" -- the decision to patch `.spec` must be based on the
    # spec itself, or unpacking None raises TypeError.
    alt = pytest.importorskip("altair")

    monkeypatch.setattr(rwb, "widget_pkg", lambda _widget: "altair")

    chart = (
        alt.Chart(alt.Data(values=[{"x": 1, "y": 2}]))
        .mark_point()
        .encode(x="x:Q", y="y:Q")
    )
    with alt.data_transformers.enable("vegafusion"):
        w = alt.JupyterChart(chart)
    assert w.spec is None

    _, fill = rwb.set_layout_defaults(w)
    assert fill is True

    assert w.chart.width == "container"
    assert w.chart.height == "container"


def test_altair_concat_chart_emits_warning(monkeypatch) -> None:
    alt = pytest.importorskip("altair")

    monkeypatch.setattr(rwb, "widget_pkg", lambda _widget: "altair")

    c1 = (
        alt.Chart(alt.Data(values=[{"x": 1, "y": 2}]))
        .mark_point()
        .encode(x="x:Q", y="y:Q")
    )
    c2 = (
        alt.Chart(alt.Data(values=[{"x": 2, "y": 3}]))
        .mark_point()
        .encode(x="x:Q", y="y:Q")
    )
    concat = alt.concat(c1, c2)
    w = alt.JupyterChart(concat)

    with pytest.warns(UserWarning, match="layout_column_wrap"):
        rwb.set_layout_defaults(w)


def test_k3d_default_height_fills() -> None:
    k3d = pytest.importorskip("k3d")

    _, fill = rwb.set_layout_defaults(k3d.plot())
    assert fill is True


def test_k3d_explicit_height_disables_fill() -> None:
    k3d = pytest.importorskip("k3d")

    _, fill = rwb.set_layout_defaults(k3d.plot(height=300))
    assert fill is False


def test_k3d_layout_height_disables_fill() -> None:
    k3d = pytest.importorskip("k3d")
    import ipywidgets as widgets

    plot = k3d.plot()
    plot.layout = widgets.Layout(height="300px")
    _, fill = rwb.set_layout_defaults(plot)
    assert fill is False


def test_k3d_height_512_is_treated_as_unset_and_fills() -> None:
    k3d = pytest.importorskip("k3d")

    _, fill = rwb.set_layout_defaults(k3d.plot(height=512))
    assert fill is True


def test_ipydatagrid_fills_unless_widget_height_is_set() -> None:
    pytest.importorskip("ipydatagrid")
    import pandas as pd
    from ipydatagrid import DataGrid

    df = pd.DataFrame({"a": [1, 2, 3]})

    _, fill = rwb.set_layout_defaults(DataGrid(df))
    assert fill is True

    _, fill = rwb.set_layout_defaults(DataGrid(df, layout={"height": "300px"}))
    assert fill is False


def _jscatter_widget() -> "Scatter":
    pytest.importorskip("jscatter")
    pd = pytest.importorskip("pandas")
    from jscatter import Scatter

    df = pd.DataFrame({"x": [0.1, 0.5, 0.9], "y": [0.3, 0.6, 0.2]})
    return Scatter(data=df, x="x", y="y")


def test_jscatter_default_height_keeps_fill_true() -> None:
    scatter = _jscatter_widget()
    _, fill = rwb.set_layout_defaults(scatter.widget)
    assert fill is True


def test_jscatter_explicit_height_disables_fill() -> None:
    scatter = _jscatter_widget()
    scatter.height(500)
    _, fill = rwb.set_layout_defaults(scatter.widget)
    assert fill is False


def test_jscatter_default_height_matches_package_default() -> None:
    # The layout default compares against jscatter's own default height, so
    # fail loudly if jscatter changes it
    scatter = _jscatter_widget()
    assert scatter.height() == rwb.JSCATTER_DEFAULT_HEIGHT


def test_jscatter_keeps_filling_after_browser_syncs_height() -> None:
    # In a filling layout the browser sets the widget's height from its
    # container's size, so displaying the same widget again (e.g., a widget
    # reused via session_lifetime()) must not mistake that for a user-set height
    widget = _jscatter_widget().widget
    assert rwb.set_layout_defaults(widget)[1] is True

    widget.height = 691
    assert rwb.set_layout_defaults(widget)[1] is True


def test_jscatter_explicit_height_stays_fixed_when_displayed_again() -> None:
    scatter = _jscatter_widget()
    scatter.height(500)
    assert rwb.set_layout_defaults(scatter.widget)[1] is False
    assert rwb.set_layout_defaults(scatter.widget)[1] is False


@pytest.mark.parametrize(
    ("sizing_mode", "expected_fill"),
    [
        ("stretch_both", True),
        ("stretch_height", True),
        ("scale_both", True),
        ("scale_height", True),
        (None, False),
        ("fixed", False),
        ("stretch_width", False),
        ("scale_width", False),
    ],
)
def test_bokeh_fills_only_when_root_stretches_vertically(
    sizing_mode: str | None, expected_fill: bool
) -> None:
    pytest.importorskip("jupyter_bokeh")
    from bokeh.plotting import figure
    from jupyter_bokeh import BokehModel

    w = BokehModel(figure(height=200, sizing_mode=sizing_mode))

    _, fill = rwb.set_layout_defaults(w)
    assert fill is expected_fill


def test_bokeh_fill_respects_upstream_decision() -> None:
    pytest.importorskip("jupyter_bokeh")
    import ipywidgets as widgets
    from bokeh.plotting import figure
    from jupyter_bokeh import BokehModel

    w = BokehModel(
        figure(sizing_mode="stretch_both"), layout=widgets.Layout(height="200px")
    )

    _, fill = rwb.set_layout_defaults(w)
    assert fill is False


def test_maplibre_default_height_fills() -> None:
    pytest.importorskip("maplibre")
    pytest.importorskip("anywidget")
    from maplibre.ipywidget import MapWidget

    for height in (400, "400px", "50%"):
        w = MapWidget(height=height)
        _, fill = rwb.set_layout_defaults(w)
        assert fill is True
        assert w.layout.height is None


def test_maplibre_explicit_height_sizes_widget_container() -> None:
    pytest.importorskip("maplibre")
    pytest.importorskip("anywidget")
    from maplibre.ipywidget import MapWidget

    # shinywidgets.css sizes the map to its widget container, so the map's
    # height has to be applied there
    w = MapWidget(height=200)
    _, fill = rwb.set_layout_defaults(w)
    assert fill is False
    assert w.layout.height == "200px"


def test_maplibre_explicit_layout_height_is_kept() -> None:
    pytest.importorskip("maplibre")
    pytest.importorskip("anywidget")
    import ipywidgets as widgets
    from maplibre.ipywidget import MapWidget

    w = MapWidget(height=200, layout=widgets.Layout(height="300px"))
    _, fill = rwb.set_layout_defaults(w)
    assert fill is False
    assert w.layout.height == "300px"
