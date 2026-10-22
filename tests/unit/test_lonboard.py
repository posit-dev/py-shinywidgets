from __future__ import annotations

import asyncio
import json
import subprocess
import sys

import pytest

pytest.importorskip(
    "lonboard",
    reason="lonboard isn't installed (e.g., it lacks wheels for this Python version)",
)

import geoarrow.rust.core as gr
import numpy as np
from arro3.core import Table
from lonboard import Map, ScatterplotLayer
from lonboard.controls import FullscreenControl
from shiny import Session, reactive
from shiny.reactive import Context
from shiny.session import session_context
from shiny.session._session import AppSession
from shinywidgets import as_widget, render_lonboard, session_lifetime
from shinywidgets._render_widget_base import WidgetRenderContext, set_layout_defaults
from shinywidgets._shinywidgets import foreign_or_closed_widget


def points_table(n: int = 5) -> Table:
    coords = (np.linspace(-10, 10, n), np.linspace(-5, 5, n))
    return Table.from_arrays([gr.points(coords, crs="EPSG:4326")], names=["geometry"])


class CustomMap(Map):
    pass


class CustomLayer(ScatterplotLayer):
    pass


@pytest.fixture
def comm_opens(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> dict[str, dict[str, object]]:
    """Initial widget states sent to the browser, keyed by model id."""
    opens: dict[str, dict[str, object]] = {}

    async def send_custom_message(type: str, message: object) -> None:
        if type == "shinywidgets_comm_open":
            assert isinstance(message, str)
            content = json.loads(message)["content"]
            opens[content["comm_id"]] = content["data"]["state"]

    monkeypatch.setattr(widget_session, "send_custom_message", send_custom_message)
    return opens


def flush(session: Session) -> None:
    assert isinstance(session, AppSession)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(reactive.flush())
    loop.run_until_complete(session._flush_callbacks.invoke())


def render(value: object, session: Session) -> render_lonboard[object]:
    r = render_lonboard()

    @r
    def _():  # noqa: ANN202
        return value

    with session_context(session):
        asyncio.run(r._render())
    return r


def test_import_lonboard_after_shinywidgets() -> None:
    code = "import shinywidgets, lonboard; print(type(lonboard.Map).__name__)"
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, proc.stderr


def test_lonboard_widgets_outside_session_still_error() -> None:
    with pytest.raises(RuntimeError, match="active Shiny session"):
        FullscreenControl()


def test_as_widget_wraps_layer_in_map(widget_session: Session) -> None:
    with session_context(widget_session):
        layer = ScatterplotLayer(table=points_table())
        res = as_widget(layer)
    assert isinstance(res, Map)
    assert res.layers == (layer,)


def test_as_widget_wraps_layer_subclass_in_map(widget_session: Session) -> None:
    with session_context(widget_session):
        layer = CustomLayer(table=points_table())
        res = as_widget(layer)
    assert isinstance(res, Map)
    assert res.layers == (layer,)


@pytest.mark.parametrize("map_class", [Map, CustomMap])
def test_open_replaces_shared_default_controls(
    widget_session: Session,
    comm_opens: dict[str, dict[str, object]],
    map_class: type[Map],
) -> None:
    # Map's default controls are constructed once, when lonboard is imported
    # (outside any session), and shared by every Map
    shared = Map.class_traits()["controls"].default()
    assert shared
    with session_context(widget_session):
        # Not constructed during a render, so its comm opens (and its state is
        # sent) before any render passes it to as_widget()
        m = map_class(ScatterplotLayer(table=points_table()))
        flush(widget_session)

    assert [type(c) for c in m.controls] == [type(c) for c in shared]
    assert not any(c in shared for c in m.controls)
    assert foreign_or_closed_widget(m, widget_session.root_scope()) is None
    # The browser has every control the Map's initial state references
    assert comm_opens[m.model_id]["controls"] == [
        f"IPY_MODEL_{c.model_id}" for c in m.controls
    ]
    assert all(c.model_id in comm_opens for c in m.controls)

    controls = m.controls
    r = render(m, widget_session)
    assert r.widget is m
    assert m.controls == controls


def test_session_lifetime_map_keeps_its_controls(widget_session: Session) -> None:
    # The per-session controls are constructed during a render, but a Map that
    # outlives that render keeps them alive
    with session_context(widget_session):
        with session_lifetime():
            m = Map(ScatterplotLayer(table=points_table()))
        context = Context()
        with context(), WidgetRenderContext():
            as_widget(m)
        asyncio.get_event_loop().run_until_complete(reactive.flush())
        context.invalidate()
        asyncio.get_event_loop().run_until_complete(reactive.flush())
    assert foreign_or_closed_widget(m, widget_session.root_scope()) is None


def test_control_copies_keep_shared_control_settings(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    shared = Map.class_traits()["controls"].default()
    assert shared
    scale = shared[2]
    monkeypatch.setattr(scale, "unit", "imperial")
    with session_context(widget_session):
        m = Map(ScatterplotLayer(table=points_table()))
        flush(widget_session)
    assert m.controls[2] is not scale
    assert m.controls[2].unit == "imperial"


def test_lonboard_first_imported_during_a_render() -> None:
    # Map's shared default controls then belong to that render (and close with
    # it), so later Maps must not reference them
    code = """
import asyncio
from shiny import App, reactive, ui
from shiny._connection import MockConnection
from shiny.reactive import Context
from shiny.session import session_context
from shinywidgets import as_widget
from shinywidgets._render_widget_base import WidgetRenderContext
from shinywidgets._shinywidgets import foreign_or_closed_widget

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
session = App(ui.page_fluid(), None)._create_session(MockConnection())
with session_context(session):
    context = Context()
    with context(), WidgetRenderContext():
        import lonboard
        as_widget(lonboard.Map([]))
    loop.run_until_complete(reactive.flush())
    context.invalidate()
    loop.run_until_complete(reactive.flush())
    with Context()(), WidgetRenderContext():
        m = as_widget(lonboard.Map([]))
    loop.run_until_complete(reactive.flush())
    assert foreign_or_closed_widget(m, session.root_scope()) is None
"""
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, proc.stderr


def test_open_keeps_user_controls(widget_session: Session) -> None:
    with session_context(widget_session):
        control = FullscreenControl()
        m = Map(ScatterplotLayer(table=points_table()), controls=[control])
        flush(widget_session)
    assert m.controls == (control,)


def test_render_lonboard_accepts_layer_list(widget_session: Session) -> None:
    with session_context(widget_session):
        layers = [ScatterplotLayer(table=points_table()) for _ in range(2)]
    r = render(layers, widget_session)
    assert isinstance(r.widget, Map)
    assert r.widget.layers == tuple(layers)


def test_render_lonboard_accepts_arrow_table(widget_session: Session) -> None:
    r = render(points_table(), widget_session)
    assert isinstance(r.widget, Map)
    assert [type(layer) for layer in r.widget.layers] == [ScatterplotLayer]
    assert foreign_or_closed_widget(r.widget, widget_session.root_scope()) is None


def test_render_lonboard_passes_through_map(widget_session: Session) -> None:
    with session_context(widget_session):
        m = Map(ScatterplotLayer(table=points_table()))
    r = render(m, widget_session)
    assert r.widget is m


def test_render_lonboard_missing_lonboard_errors(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "lonboard", None)
    with pytest.raises(ImportError, match=r"pip install lonboard"):
        render(points_table(), widget_session)


@pytest.mark.parametrize("map_class", [Map, CustomMap])
def test_default_height_fills(widget_session: Session, map_class: type[Map]) -> None:
    with session_context(widget_session):
        m = map_class(ScatterplotLayer(table=points_table()))
    _, fill = set_layout_defaults(m)
    assert fill is True
    # lonboard's default height is kept: it's the map's size when there's no
    # definite height to fill (and shinywidgets.css clamps it to the container)
    assert m.height == "500px"
    assert m.layout.height == "100%"


def test_explicit_height_is_respected(widget_session: Session) -> None:
    with session_context(widget_session):
        m = Map(ScatterplotLayer(table=points_table()), height=300)
    _, fill = set_layout_defaults(m)
    assert fill is False
    assert m.height == "300px"
    # The map's min-height is its widget container's height, so the container
    # must size to the map (not to its parent) for `height` to take effect
    assert m.layout.height == "auto"


def test_explicit_layout_height_is_respected(widget_session: Session) -> None:
    with session_context(widget_session):
        m = Map(ScatterplotLayer(table=points_table()))
        m.layout.height = "300px"
    _, fill = set_layout_defaults(m)
    assert fill is False
    assert m.height == "500px"
    assert m.layout.height == "300px"


def test_explicit_full_height_fills(widget_session: Session) -> None:
    with session_context(widget_session):
        m = Map(ScatterplotLayer(table=points_table()), height="100%")
    _, fill = set_layout_defaults(m)
    assert fill is True
