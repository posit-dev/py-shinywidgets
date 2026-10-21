import pytest
import shinywidgets._render_widget_base as rwb


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

    spec = w.chart.to_dict()
    assert spec.get("width") == "container"
    assert spec.get("height") == "container"


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


def _jscatter_widget():  # noqa: ANN202
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
