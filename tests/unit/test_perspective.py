import asyncio
import sys
from typing import Callable

import pytest
import shinywidgets._render_widget as rw
from htmltools import HTMLDependency, TagChild, TagList
from shiny import reactive
from shiny.session import Session, session_context
from shiny.session._session import RenderedDeps
from shinywidgets._as_widget import as_widget

perspective = pytest.importorskip("perspective")
pd = pytest.importorskip("pandas")
pytest.importorskip("pyarrow")

from perspective.widget import PerspectiveWidget  # noqa: E402


def render(renderer: rw.render_perspective, value: object) -> object:
    @renderer
    def _():  # noqa: ANN202
        return value

    return asyncio.run(renderer._render())


def test_as_widget_perspective_table(widget_session) -> None:
    table = perspective.table({"a": [1, 2, 3]})
    with session_context(widget_session):
        res = as_widget(table)
    assert isinstance(res, PerspectiveWidget)
    assert res.table is table
    assert res.table_name == table.get_name()


def test_render_perspective_accepts_dataframe(widget_session) -> None:
    r = rw.render_perspective()
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    with session_context(widget_session):
        res = render(r, df)

    assert res is not None
    assert isinstance(r.widget, PerspectiveWidget)
    assert r.widget.table.size() == 3
    assert {"a", "b"} <= set(r.widget.table.columns())


def test_render_perspective_accepts_polars_dataframe(widget_session) -> None:
    pl = pytest.importorskip("polars")
    r = rw.render_perspective()
    with session_context(widget_session):
        assert render(r, pl.DataFrame({"a": [1, 2, 3]})) is not None
    assert isinstance(r.widget, PerspectiveWidget)
    assert r.widget.table.size() == 3


def test_render_perspective_accepts_table(widget_session) -> None:
    r = rw.render_perspective()
    table = perspective.table({"a": [1, 2]})
    with session_context(widget_session):
        assert render(r, table) is not None
    assert isinstance(r.widget, PerspectiveWidget)
    assert r.widget.table is table


def test_render_perspective_accepts_widget(widget_session) -> None:
    r = rw.render_perspective()
    with session_context(widget_session):
        widget = PerspectiveWidget({"a": [1, 2]}, plugin="Datagrid")
        assert render(r, widget) is not None
    assert r.widget is widget


def test_render_perspective_rejects_unsupported_value(widget_session) -> None:
    class Unsupported:
        pass

    r = rw.render_perspective()
    with session_context(widget_session):
        with pytest.raises(TypeError, match="Don't know how to coerce"):
            render(r, Unsupported())


def test_render_perspective_dataframe_requires_perspective_widget(
    widget_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "perspective.widget", None)
    r = rw.render_perspective()
    with session_context(widget_session):
        with pytest.raises(ImportError, match=r"pip install perspective-python"):
            render(r, pd.DataFrame({"a": [1]}))


def comm_open_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    widget_session: Session,
    make_widget: Callable[[], object],
) -> list[HTMLDependency]:
    dependencies: list[HTMLDependency] = []
    process_ui = widget_session._process_ui

    def capture_dependencies(value: TagChild) -> RenderedDeps:
        if isinstance(value, TagList):
            dependencies.extend(value.get_dependencies())
        return process_ui(value)

    monkeypatch.setattr(widget_session, "_process_ui", capture_dependencies)
    with session_context(widget_session):
        make_widget()
        asyncio.run(reactive.flush())
    return dependencies


def test_perspective_comm_open_includes_custom_element_guard(
    monkeypatch: pytest.MonkeyPatch, widget_session: Session
) -> None:
    dependencies = comm_open_dependencies(
        monkeypatch, widget_session, lambda: PerspectiveWidget({"a": [1]})
    )

    # Perspective's ESM registers custom elements at module scope, and anywidget
    # evaluates it once per model, so a second model in the page (e.g., after a
    # re-render) fails to initialize unless redefinition is ignored
    guards = [dep for dep in dependencies if dep.name == "shinywidgets-custom-elements"]
    assert len(guards) == 1
    assert "customElements.define" in str(guards[0].head)


def test_other_widgets_do_not_get_custom_element_guard(
    monkeypatch: pytest.MonkeyPatch, widget_session: Session
) -> None:
    import ipywidgets

    dependencies = comm_open_dependencies(
        monkeypatch, widget_session, lambda: ipywidgets.IntSlider()
    )
    assert not any(dep.name == "shinywidgets-custom-elements" for dep in dependencies)
