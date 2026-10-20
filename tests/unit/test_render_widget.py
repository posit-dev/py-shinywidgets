import asyncio

import pytest
import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
from htmltools import HTMLDependency, div
from shiny.session import session_context


def test_render_maplibre_is_render_widget_base() -> None:
    renderer = rw.render_maplibre()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_plotly_accepts_figure_config_tuple(widget_session) -> None:
    pytest.importorskip("plotly")
    import plotly.graph_objects as go

    r = rw.render_plotly()

    @r
    def _():  # noqa: ANN202
        return (go.Figure(), {"displayModeBar": False})

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert res is not None
    assert isinstance(r.widget, go.FigureWidget)
    assert r.widget._config["displayModeBar"] is False  # type: ignore
    # the user's config is merged over plotly's (and shinywidgets') defaults
    assert "plotlyServerURL" in r.widget._config  # type: ignore


def test_render_plotly_accepts_figurewidget_config_tuple(widget_session) -> None:
    pytest.importorskip("plotly")
    import plotly.graph_objects as go

    r = rw.render_plotly()
    created = []

    @r
    def _():  # noqa: ANN202
        fw = go.FigureWidget()
        created.append(fw)
        return (fw, {"displayModeBar": False})

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert res is not None
    # a pre-built FigureWidget is passed through as-is (not re-coerced)
    assert r.widget is created[0]
    assert r.widget._config["displayModeBar"] is False  # type: ignore


def test_render_plotly_config_tuple_overrides_shinywidgets_defaults(
    widget_session,
) -> None:
    pytest.importorskip("plotly")
    import plotly.graph_objects as go

    r = rw.render_plotly()

    @r
    def _():  # noqa: ANN202
        # shinywidgets defaults responsive to True (in filling layouts)
        return (go.Figure(), {"responsive": False})

    with session_context(widget_session):
        assert asyncio.run(r._render()) is not None
    assert r.widget._config["responsive"] is False  # type: ignore


def test_render_plotly_malformed_tuple_errors(widget_session) -> None:
    pytest.importorskip("plotly")
    import plotly.graph_objects as go

    r = rw.render_plotly()

    @r
    def _():  # noqa: ANN202
        return (go.Figure(), "displayModeBar=False")

    with session_context(widget_session):
        with pytest.raises(TypeError, match=r"\(figure, config\) tuple"):
            asyncio.run(r._render())


def test_render_plotly_plain_figure_still_works(widget_session) -> None:
    pytest.importorskip("plotly")
    import plotly.graph_objects as go

    r = rw.render_plotly()

    @r
    def _():  # noqa: ANN202
        return go.Figure()

    with session_context(widget_session):
        assert asyncio.run(r._render()) is not None
    assert isinstance(r.widget, go.FigureWidget)
    assert r.widget._config.get("responsive") is True  # type: ignore


def test_render_bokeh_auto_output_ui_appends_bokeh_dependency(monkeypatch) -> None:
    sentinel = HTMLDependency(
        name="bokeh-inline",
        version="1.0",
        source={"href": "https://example.invalid"},
    )

    monkeypatch.setattr(rwb, "output_widget", lambda *args, **kwargs: div())
    monkeypatch.setattr(rw, "bokeh_dependency", lambda: sentinel)

    renderer = rw.render_bokeh()
    renderer.output_id = "plot"

    res = renderer.auto_output_ui()

    assert any(dep.name == "bokeh-inline" for dep in res.get_dependencies())


def test_render_panel_and_hvplot_auto_output_ui_append_bokeh_dependency(
    monkeypatch,
) -> None:
    sentinel = HTMLDependency(
        name="bokeh-inline",
        version="1.0",
        source={"href": "https://example.invalid"},
    )

    monkeypatch.setattr(rwb, "output_widget", lambda *args, **kwargs: div())
    monkeypatch.setattr(rw, "bokeh_dependency", lambda: sentinel)

    for cls in (rw.render_panel, rw.render_holoviews):
        renderer = cls()
        renderer.output_id = "plot"

        res = renderer.auto_output_ui()

        assert any(dep.name == "bokeh-inline" for dep in res.get_dependencies()), cls
