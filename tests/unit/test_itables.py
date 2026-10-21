from __future__ import annotations

import asyncio
import sys

import pytest
import shinywidgets
import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
from shiny import Session
from shiny.session import session_context

pytest.importorskip("itables")
pytest.importorskip("anywidget")

from itables.widget import ITable  # noqa: E402


def render(renderer: rw.render_itables, session: Session) -> dict:
    with session_context(session):
        res = asyncio.run(renderer._render())
    assert isinstance(res, dict)
    return res


def test_render_itables_is_exported_render_widget_base() -> None:
    assert shinywidgets.render_itables is rw.render_itables
    assert "render_itables" in shinywidgets.__all__
    assert "render_itables" in rw.__all__
    assert isinstance(rw.render_itables(), rwb.render_widget_base)


def test_pandas_dataframe_is_coerced_to_itable(widget_session: Session) -> None:
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"a": [1, 2, 3]})

    r = rw.render_itables()
    r(lambda: df)
    render(r, widget_session)

    assert isinstance(r.widget, ITable)
    assert r.widget.df is df
    assert r.value is df


def test_polars_dataframe_is_coerced_to_itable(widget_session: Session) -> None:
    pl = pytest.importorskip("polars")
    df = pl.DataFrame({"a": [1, 2, 3]})

    r = rw.render_itables()
    r(lambda: df)
    render(r, widget_session)

    assert isinstance(r.widget, ITable)


def test_itable_widget_is_passed_through(widget_session: Session) -> None:
    pd = pytest.importorskip("pandas")
    created: list[ITable] = []

    def fn() -> ITable:
        w = ITable(pd.DataFrame({"a": [1]}), select=True, selected_rows=[0])
        created.append(w)
        return w

    r = rw.render_itables()
    r(fn)
    render(r, widget_session)

    assert r.widget is created[0]
    assert r.widget.selected_rows == [0]


def test_unsupported_value_raises_type_error(widget_session: Session) -> None:
    r = rw.render_itables()
    r(lambda: object())
    with pytest.raises(TypeError, match="Unsupported dataframe type"):
        render(r, widget_session)


def test_missing_itables_gives_install_hint(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "itables.widget", None)
    r = rw.render_itables()
    r(lambda: [1, 2, 3])
    with pytest.raises(ImportError, match=r"pip install 'itables\[widget\]'"):
        render(r, widget_session)


def test_default_layout_fills(widget_session: Session) -> None:
    pd = pytest.importorskip("pandas")
    r = rw.render_itables()
    r(lambda: pd.DataFrame({"a": [1]}))
    assert render(r, widget_session)["fill"] is True


def test_default_scroll_height_fills_container(widget_session: Session) -> None:
    pd = pytest.importorskip("pandas")
    r = rw.render_itables()
    r(lambda: pd.DataFrame({"a": [1]}))
    render(r, widget_session)
    assert r.widget is not None
    assert r.widget._dt_args["scrollY"] == "100%"


def test_explicit_scroll_height_is_respected(widget_session: Session) -> None:
    pd = pytest.importorskip("pandas")
    r = rw.render_itables()
    r(lambda: ITable(pd.DataFrame({"a": [1]}), scrollY="300px"))
    render(r, widget_session)
    assert r.widget is not None
    assert r.widget._dt_args["scrollY"] == "300px"


def test_layout_height_disables_fill_but_still_scrolls(
    widget_session: Session,
) -> None:
    pd = pytest.importorskip("pandas")
    r = rw.render_itables()

    def fn() -> ITable:
        w = ITable(pd.DataFrame({"a": [1]}))
        w.layout.height = "300px"
        return w

    r(fn)
    assert render(r, widget_session)["fill"] is False
    assert r.widget is not None
    assert r.widget._dt_args["scrollY"] == "100%"


def test_default_style_is_full_width_when_scrolling(widget_session: Session) -> None:
    pd = pytest.importorskip("pandas")
    r = rw.render_itables()
    r(lambda: pd.DataFrame({"a": [1]}))
    render(r, widget_session)
    assert r.widget is not None
    assert "width:100%" in r.widget.style
    assert "width:auto" not in r.widget.style


def test_explicit_style_is_respected(widget_session: Session) -> None:
    pd = pytest.importorskip("pandas")
    r = rw.render_itables()
    r(lambda: ITable(pd.DataFrame({"a": [1]}), style="width:50%"))
    render(r, widget_session)
    assert r.widget is not None
    assert r.widget.style == "width:50%"
