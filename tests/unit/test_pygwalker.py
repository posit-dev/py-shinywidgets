from __future__ import annotations

import asyncio
import sys

import pytest
import shinywidgets
import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
from shiny.session import session_context

pytest.importorskip("pygwalker")

import pandas as pd  # noqa: E402
from pygwalker.api.anywidget import _WalkerWidget  # noqa: E402


@pytest.fixture(autouse=True)
def _offline_pygwalker(monkeypatch: pytest.MonkeyPatch):
    # pygwalker phones home (update check, usage events) when it builds a walker
    from pygwalker import GlobalVarManager

    monkeypatch.setattr(GlobalVarManager, "privacy", "offline")


def render(value: object, widget_session) -> rw.render_pygwalker:
    r = rw.render_pygwalker()

    @r
    def _():  # noqa: ANN202
        return value

    with session_context(widget_session):
        assert asyncio.run(r._render()) is not None
    return r


def test_render_pygwalker_is_exported() -> None:
    assert shinywidgets.render_pygwalker is rw.render_pygwalker
    assert "render_pygwalker" in shinywidgets.__all__
    assert "render_pygwalker" in rw.__all__


def test_dataframe_is_coerced_to_walker_widget(widget_session) -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    r = render(df, widget_session)
    assert isinstance(r.widget, _WalkerWidget)
    assert r.value is df
    assert '"a"' in r.widget.props


def test_dataframe_subclass_is_coerced_to_walker_widget(widget_session) -> None:
    class MyFrame(pd.DataFrame):
        pass

    r = render(MyFrame({"a": [1, 2, 3]}), widget_session)
    assert isinstance(r.widget, _WalkerWidget)


def test_polars_dataframe_gets_pandas_hint(widget_session) -> None:
    # PyGWalker's polars support is broken with polars >= 1.0, so don't hand it one.
    # (A stand-in is enough: only the type's package and name are inspected.)
    DataFrame = type("DataFrame", (), {"__module__": "polars.dataframe.frame"})
    r = rw.render_pygwalker()

    @r
    def _():  # noqa: ANN202
        return DataFrame()

    with session_context(widget_session):
        with pytest.raises(TypeError, match=r"to_pandas\(\)"):
            asyncio.run(r._render())


def test_prebuilt_walker_widget_is_passed_through(widget_session) -> None:
    from pygwalker.api.anywidget import walk

    with session_context(widget_session):
        w = walk(pd.DataFrame({"a": [1, 2, 3]}), theme_key="vega")
    r = render(w, widget_session)
    assert r.widget is w


def test_unsupported_value_raises_type_error(widget_session) -> None:
    class NotAFrame:
        pass

    r = rw.render_pygwalker()

    @r
    def _():  # noqa: ANN202
        return NotAFrame()

    with session_context(widget_session):
        with pytest.raises(TypeError, match="coerce"):
            asyncio.run(r._render())


def test_missing_pygwalker_gives_install_hint(
    monkeypatch: pytest.MonkeyPatch, widget_session
) -> None:
    monkeypatch.setitem(sys.modules, "pygwalker.api.anywidget", None)
    r = rw.render_pygwalker()

    @r
    def _():  # noqa: ANN202
        return pd.DataFrame({"a": [1]})

    with session_context(widget_session):
        with pytest.raises(
            ImportError, match=r"pip install 'shinywidgets\[pygwalker\]'"
        ):
            asyncio.run(r._render())


def layout_defaults(widget_session, **layout: str) -> tuple[_WalkerWidget, bool]:
    from pygwalker.api.anywidget import walk

    with session_context(widget_session):
        w = walk(pd.DataFrame({"a": [1, 2, 3]}))
        for k, v in layout.items():
            setattr(w.layout, k, v)
        _, fill = rwb.set_layout_defaults(w)
    return w, fill


def test_layout_defaults_scroll_within_container(widget_session) -> None:
    # PyGWalker's UI has a minimum height, so it must scroll (not be clipped)
    # when the container, or an explicit height, is shorter than that
    w, fill = layout_defaults(widget_session)
    assert fill is True
    assert w.layout.overflow == "auto"
    assert w.layout.height == "100%"


def test_layout_defaults_respect_explicit_height(widget_session) -> None:
    w, fill = layout_defaults(widget_session, height="300px")
    assert fill is False
    assert w.layout.height == "300px"
    assert w.layout.overflow == "auto"


def test_layout_defaults_respect_explicit_overflow(widget_session) -> None:
    w, _ = layout_defaults(widget_session, overflow="visible")
    assert w.layout.overflow == "visible"


def test_layout_defaults_are_idempotent_across_renders(widget_session) -> None:
    # A widget that's rendered again (e.g., reused via session_lifetime()) must
    # keep filling, even though the first pass wrote layout.height
    from pygwalker.api.anywidget import walk

    with session_context(widget_session):
        w = walk(pd.DataFrame({"a": [1, 2, 3]}))
        fills = [rwb.set_layout_defaults(w)[1] for _ in range(3)]
    assert fills == [True, True, True]
    assert w.layout.height == "100%"
