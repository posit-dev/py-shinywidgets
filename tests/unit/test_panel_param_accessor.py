from __future__ import annotations

import asyncio
from typing import Any, Callable

import pandas as pd
import param
import pytest
from shiny import Session
from shiny.reactive._core import Context
from shiny.session import session_context
from shinywidgets import render_panel
from shinywidgets._render_widget_base import WidgetRenderContext


class Gauge(param.Parameterized):
    value = param.Integer(default=0)
    label = param.String(default="a")
    xs = param.List(default=[])
    clicked = param.Event()


def watcher_count(obj: param.Parameterized, name: str) -> int:
    # Count only the accessor's watcher (panel adds its own when rendering)
    watchers = obj.param.watchers.get(name, {}).get("value", [])
    return len([w for w in watchers if w.fn.__name__ == "on_change"])


def make_renderer(session: Session, fn: Callable[[], Any]) -> render_panel:
    with session_context(session):

        @render_panel
        def out():
            return fn()

    return out


def do_render(session: Session, renderer: render_panel) -> None:
    with session_context(session):
        context = Context()
        with context():
            with WidgetRenderContext():
                asyncio.run(renderer._render())


def test_param_is_seeded_at_render(widget_session: Session) -> None:
    gauge = Gauge(value=3, label="b")
    r = make_renderer(widget_session, lambda: gauge)
    do_render(widget_session, r)
    with session_context(widget_session):
        assert r.param("value") == 3
        assert r.param("label") == "b"


def test_param_change_invalidates_a_reader(widget_session: Session) -> None:
    gauge = Gauge(value=0)
    r = make_renderer(widget_session, lambda: gauge)
    do_render(widget_session, r)
    with session_context(widget_session):
        reader = Context()
        with reader():
            assert r.param("value") == 0
        # The browser syncs param changes the same way Python sets them
        gauge.value = 7
        assert reader._invalidated
        assert r.param("value") == 7


def test_rerender_reattaches_to_the_new_value(widget_session: Session) -> None:
    current = {"gauge": Gauge(value=1)}
    r = make_renderer(widget_session, lambda: current["gauge"])
    do_render(widget_session, r)
    old = current["gauge"]
    with session_context(widget_session):
        reader = Context()
        with reader():
            assert r.param("value") == 1
        assert watcher_count(old, "value") == 1

        new = Gauge(value=5)
        current["gauge"] = new
        do_render(widget_session, r)

        # The old object is no longer watched; the new one is
        assert watcher_count(old, "value") == 0
        assert watcher_count(new, "value") == 1
        # The reader re-ran and sees the new object's seeded value
        assert reader._invalidated
        assert r.param("value") == 5
        # Changes to the old object no longer reach the accessor
        old.value = 9
        assert r.param("value") == 5
        new.value = 8
        assert r.param("value") == 8


def test_rerender_with_equal_param_value_follows_the_new_object(
    widget_session: Session,
) -> None:
    # An equal-but-fresh parameter value must still republish: readers should
    # hold the new object's list, not the old one's
    current = {"gauge": Gauge(xs=[1, 2])}
    r = make_renderer(widget_session, lambda: current["gauge"])
    do_render(widget_session, r)
    with session_context(widget_session):
        assert r.param("xs") == [1, 2]
        new = Gauge(xs=[1, 2])
        current["gauge"] = new
        do_render(widget_session, r)
        assert r.param("xs") is new.xs


def test_in_place_mutation_and_trigger_invalidates(widget_session: Session) -> None:
    # param can't see in-place mutation, so users call param.trigger() -- the
    # documented idiom -- which fires with event.new is event.old
    gauge = Gauge(xs=[1, 2])
    r = make_renderer(widget_session, lambda: gauge)
    do_render(widget_session, r)
    with session_context(widget_session):
        reader = Context()
        with reader():
            assert r.param("xs") == [1, 2]
        gauge.xs.append(3)
        gauge.param.trigger("xs")
        assert reader._invalidated
        assert r.param("xs") == [1, 2, 3]


def test_event_parameter_fires_on_every_trigger(widget_session: Session) -> None:
    # param.Event is a pulse by design: repeated identical firings each count
    gauge = Gauge()
    r = make_renderer(widget_session, lambda: gauge)
    do_render(widget_session, r)
    with session_context(widget_session):
        reader = Context()
        with reader():
            r.param("clicked")
        gauge.param.trigger("clicked")
        assert reader._invalidated
        # Dependencies are one-shot: the reader re-runs (re-reads) before the
        # next pulse can invalidate it again
        reader._invalidated = False
        with reader():
            r.param("clicked")
        gauge.param.trigger("clicked")
        assert reader._invalidated


def test_failed_rerender_unwatches_the_previous_value(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # _render() replaces .value before coercion; if coercion then fails, the
    # accessor must not keep watching (and reporting) the previous object
    gauge = Gauge(value=1)
    r = make_renderer(widget_session, lambda: gauge)
    do_render(widget_session, r)

    def fail(value: object) -> None:
        raise RuntimeError("coercion failed")

    class Cancel(Exception):
        pass

    def cancel(*args: object) -> None:
        raise Cancel()

    import shinywidgets._accessors as acc

    with session_context(widget_session):
        assert r.param("value") == 1
        assert watcher_count(gauge, "value") == 1
        monkeypatch.setattr(r, "_as_widget", fail)
        with pytest.raises(RuntimeError, match="coercion failed"):
            do_render(widget_session, r)
        # The old object is unwatched, so its changes no longer invalidate
        assert watcher_count(gauge, "value") == 0
        # ...and reads cancel while the output has no rendered widget
        monkeypatch.setattr(acc, "req", cancel)
        with pytest.raises(Cancel):
            r.param("value")


def test_param_requires_a_parameterized_value(widget_session: Session) -> None:
    # render_panel renders anything pn.panel() accepts; a raw value like a
    # DataFrame has no parameters to read
    r = make_renderer(widget_session, lambda: pd.DataFrame({"x": [1, 2, 3]}))
    do_render(widget_session, r)  # rendering itself succeeds
    with session_context(widget_session):
        with pytest.raises(TypeError, match="param\\.Parameterized"):
            r.param("value")


def test_param_requires_an_existing_parameter(widget_session: Session) -> None:
    r = make_renderer(widget_session, lambda: Gauge())
    do_render(widget_session, r)
    with session_context(widget_session):
        with pytest.raises(ValueError, match="'nope'"):
            r.param("nope")


def test_param_read_before_render_cancels(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shinywidgets._accessors as acc

    r = make_renderer(widget_session, lambda: Gauge())

    class Cancel(Exception):
        pass

    def cancel(*args: object) -> None:
        raise Cancel()

    monkeypatch.setattr(acc, "req", cancel)
    with session_context(widget_session):
        with pytest.raises(Cancel):
            r.param("value")


def test_param_cant_be_read_inside_its_own_render(widget_session: Session) -> None:
    with session_context(widget_session):

        @render_panel
        def out():
            out.param("value")
            return Gauge()

        context = Context()
        with context():
            with WidgetRenderContext():
                with pytest.raises(RuntimeError, match="own render function"):
                    asyncio.run(out._render())


def test_session_end_unwatches(widget_session: Session) -> None:
    gauge = Gauge(value=1)
    r = make_renderer(widget_session, lambda: gauge)
    do_render(widget_session, r)
    with session_context(widget_session):
        assert r.param("value") == 1
        assert watcher_count(gauge, "value") == 1

    asyncio.run(widget_session.close())

    assert watcher_count(gauge, "value") == 0


def test_close_unwatches_and_a_rerender_watches_again(
    widget_session: Session,
) -> None:
    gauge = Gauge(value=1)
    r = make_renderer(widget_session, lambda: gauge)
    do_render(widget_session, r)
    with session_context(widget_session):
        assert r.param("value") == 1
        assert watcher_count(gauge, "value") == 1
        r._accessors.close()
        assert watcher_count(gauge, "value") == 0


def test_panel_widget_param_follows_browser_style_changes(
    widget_session: Session,
) -> None:
    # A real panel widget: bokeh-synced param changes (what the browser does)
    # invalidate readers just like Python-side ones
    import panel as pn

    slider = pn.widgets.IntSlider(value=2, start=0, end=10)
    r = make_renderer(widget_session, lambda: slider)
    do_render(widget_session, r)
    with session_context(widget_session):
        reader = Context()
        with reader():
            assert r.param("value") == 2
        assert watcher_count(slider, "value") == 1
        slider.value = 6
        assert reader._invalidated
        assert r.param("value") == 6
        r._accessors.close()
        assert watcher_count(slider, "value") == 0
