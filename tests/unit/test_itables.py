from __future__ import annotations

import asyncio
import json
import sys

import pytest
import shinywidgets
import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
from ipywidgets import Widget
from shiny import Session, reactive
from shiny.session import session_context
from shiny.session._session import AppSession

pytest.importorskip("itables")
pytest.importorskip("anywidget")

from itables.widget import ITable  # noqa: E402

FILL_CLASS = "shinywidgets-itables-fill"


def render(renderer: rw.render_itables, session: Session) -> dict:
    with session_context(session):
        res = asyncio.run(renderer._render())
    assert isinstance(res, dict)
    return res


def test_render_itables_is_exported_render_widget_base() -> None:
    assert shinywidgets.render_itables is rw.render_itables
    assert "render_itables" in shinywidgets.__all__
    assert "render_itables" in rw.__all__


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
    assert FILL_CLASS in r.widget._dom_classes


def test_explicit_scroll_height_is_respected(widget_session: Session) -> None:
    pd = pytest.importorskip("pandas")
    r = rw.render_itables()
    r(lambda: ITable(pd.DataFrame({"a": [1]}), scrollY="300px"))
    render(r, widget_session)
    assert r.widget is not None
    assert r.widget._dt_args["scrollY"] == "300px"
    assert FILL_CLASS not in r.widget._dom_classes


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


def test_explicit_width_auto_style_is_respected(widget_session: Session) -> None:
    pd = pytest.importorskip("pandas")
    r = rw.render_itables()
    r(lambda: ITable(pd.DataFrame({"a": [1]}), style="width:auto"))
    render(r, widget_session)
    assert r.widget is not None
    assert r.widget.style == "width:auto"
    assert r.widget._dt_args["scrollY"] == "100%"


def test_default_style_is_full_width_with_scroll_x(widget_session: Session) -> None:
    # itables rewrites the default margin:auto to margin:0 when scrollX is set; the
    # width fix must still recognize that as the default style
    pd = pytest.importorskip("pandas")
    r = rw.render_itables()
    r(lambda: ITable(pd.DataFrame({"a": [1]}), scrollX=True))
    render(r, widget_session)
    assert r.widget is not None
    assert "width:100%" in r.widget.style
    assert "margin:0" in r.widget.style


def test_explicit_style_is_respected_with_scroll_x(widget_session: Session) -> None:
    pd = pytest.importorskip("pandas")
    r = rw.render_itables()
    r(lambda: ITable(pd.DataFrame({"a": [1]}), scrollX=True, style="width:50%"))
    render(r, widget_session)
    assert r.widget is not None
    assert r.widget.style == "width:50%"


def test_update_scroll_height_drops_fill_marker(widget_session: Session) -> None:
    pd = pytest.importorskip("pandas")
    r = rw.render_itables()
    r(lambda: pd.DataFrame({"a": [1]}))
    render(r, widget_session)
    assert r.widget is not None
    assert FILL_CLASS in r.widget._dom_classes

    r.widget.update(scrollY="150px")
    assert r.widget._dt_args["scrollY"] == "150px"
    assert FILL_CLASS not in r.widget._dom_classes


def test_update_scroll_height_to_none_drops_fill_marker(
    widget_session: Session,
) -> None:
    pd = pytest.importorskip("pandas")
    r = rw.render_itables()
    r(lambda: pd.DataFrame({"a": [1]}))
    render(r, widget_session)
    assert r.widget is not None

    r.widget.update(scrollY=None)
    assert "scrollY" not in r.widget._dt_args
    assert FILL_CLASS not in r.widget._dom_classes


def test_update_keeping_default_scroll_height_keeps_fill_marker(
    widget_session: Session,
) -> None:
    pd = pytest.importorskip("pandas")
    r = rw.render_itables()
    r(lambda: pd.DataFrame({"a": [1]}))
    render(r, widget_session)
    assert r.widget is not None

    r.widget.update(pd.DataFrame({"a": [1, 2]}))
    assert r.widget._dt_args["scrollY"] == "100%"
    assert FILL_CLASS in r.widget._dom_classes


def test_layout_defaults_are_idempotent(widget_session: Session) -> None:
    pd = pytest.importorskip("pandas")
    with session_context(widget_session):
        w = ITable(pd.DataFrame({"a": [1]}))
        rwb.set_layout_defaults(w)
        first = (dict(w._dt_args), w.style, list(w._dom_classes))
        rwb.set_layout_defaults(w)
    assert (dict(w._dt_args), w.style, list(w._dom_classes)) == first
    assert w._dom_classes.count(FILL_CLASS) == 1


def comm_open_contents(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch, make: type[Widget]
) -> dict[str, object]:
    messages: list[str] = []

    async def send_custom_message(type: str, message: object) -> None:
        if type == "shinywidgets_comm_open":
            assert isinstance(message, str)
            messages.append(message)

    monkeypatch.setattr(widget_session, "send_custom_message", send_custom_message)
    assert isinstance(widget_session, AppSession)
    with session_context(widget_session):
        widget = make()
        asyncio.get_event_loop().run_until_complete(reactive.flush())
        asyncio.get_event_loop().run_until_complete(
            widget_session._flush_callbacks.invoke()
        )
    return next(
        msg["content"]
        for msg in map(json.loads, messages)
        if msg["content"]["comm_id"] == widget.model_id
    )


def test_itable_comm_open_asks_client_to_protect_page_jquery(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = comm_open_contents(widget_session, monkeypatch, ITable)
    assert content["protect_jquery"] is True


class CustomITable(ITable):
    pass


def test_itable_subclass_comm_open_asks_client_to_protect_page_jquery(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = comm_open_contents(widget_session, monkeypatch, CustomITable)
    assert content["protect_jquery"] is True


def test_other_widget_comm_open_does_not_protect_page_jquery(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = comm_open_contents(widget_session, monkeypatch, Widget)
    assert "protect_jquery" not in content
