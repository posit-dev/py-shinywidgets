import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
from htmltools import HTMLDependency, div


def test_render_maplibre_is_render_widget_base() -> None:
    renderer = rw.render_maplibre()
    assert isinstance(renderer, rwb.render_widget_base)


def test_render_matplotlib_is_render_widget_base() -> None:
    renderer = rw.render_matplotlib()
    assert isinstance(renderer, rwb.render_widget_base)


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
