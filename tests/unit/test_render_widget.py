from htmltools import HTMLDependency, div

import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb


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
