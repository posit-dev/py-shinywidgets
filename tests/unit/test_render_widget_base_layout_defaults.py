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


def test_ipyvolume_default_size_fills() -> None:
    pytest.importorskip("ipyvolume")
    import ipyvolume as ipv

    # Both construction paths' default canvas sizes count as "unset": the
    # trait default (500x400) and ipv.figure()'s (400x500)
    for w in (ipv.Figure(), ipv.figure()):
        _, fill = rwb.set_layout_defaults(w)
        assert fill is True


def test_ipyvolume_explicit_size_disables_fill() -> None:
    pytest.importorskip("ipyvolume")
    import ipyvolume as ipv

    for w in (ipv.Figure(height=300), ipv.figure(width=800), ipv.figure(height=300)):
        _, fill = rwb.set_layout_defaults(w)
        assert fill is False


def test_ipyvolume_browser_synced_size_still_fills() -> None:
    # When a cached, session-lifetime figure is redisplayed, its width/height
    # may hold the size the browser resizer measured and synced back (a
    # front-end "update" message, which arrives via Widget.set_state()). That
    # must not be mistaken for an explicit user size.
    pytest.importorskip("ipyvolume")
    import ipyvolume as ipv

    w = ipv.figure()
    _, fill = rwb.set_layout_defaults(w)
    assert fill is True

    # The browser resizer saves its measured canvas size back to Python
    w.set_state({"width": 800, "height": 390})
    assert (w.width, w.height) == (800, 390)

    _, fill = rwb.set_layout_defaults(w)
    assert fill is True


def test_ipyvolume_user_resize_after_browser_sync_disables_fill() -> None:
    # An intentional size change in Python (after the browser's sync) is an
    # explicit user size, so the output should stop filling
    pytest.importorskip("ipyvolume")
    import ipyvolume as ipv

    w = ipv.figure()
    rwb.set_layout_defaults(w)
    w.set_state({"width": 800, "height": 390})

    w.height = 300
    _, fill = rwb.set_layout_defaults(w)
    assert fill is False
