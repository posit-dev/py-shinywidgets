"""
The browser can open a comm of its own (a widget's JavaScript creating a model,
e.g. bqplot's toolbar PanZoom or pythreejs light targets). Such a comm_open
constructs the Python counterpart through ipywidgets' own handler, so trait
references to the model resolve, and a comm_close from the browser closes it.

A browser-created widget takes the lifetime of whatever the browser attaches it
to: once a browser message names it, it closes when nothing live in the session
references it anymore.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any, Dict, List, cast

import ipywidgets
import pytest
import shinywidgets._shinywidgets as sw
from shiny import App, Session, reactive, ui
from shiny._connection import MockConnection
from shiny.reactive._core import Context
from shiny.session import session_context
from shinywidgets import session_lifetime, shared_lifetime
from shinywidgets._comm import ShinyComm
from shinywidgets._render_widget_base import WidgetRenderContext, is_closed_widget
from shinywidgets._widget_registry import WIDGET_INSTANCE_MAP

from tests.unit.conftest import widget_test_server

CONTROLS = ipywidgets._version.__jupyter_widgets_controls_version__
PROTOCOL = ipywidgets._version.__protocol_version__


def flush() -> None:
    asyncio.get_event_loop().run_until_complete(reactive.flush())


def model_state(model: str, view: str, **traits: Any) -> Dict[str, Any]:
    return {
        "_model_module": "@jupyter-widgets/controls",
        "_model_module_version": CONTROLS,
        "_model_name": model,
        "_view_module": "@jupyter-widgets/controls",
        "_view_module_version": CONTROLS,
        "_view_name": view,
        **traits,
    }


def open_msg(
    comm_id: str,
    state: Dict[str, Any],
    *,
    target: str = "jupyter.widget",
    buffer_paths: List[List[str]] | None = None,
    buffers: List[str] | None = None,
) -> Dict[str, Any]:
    data: Dict[str, Any] = {"state": state}
    if buffer_paths is not None:
        data["buffer_paths"] = buffer_paths
    return {
        "header": {"msg_id": f"{comm_id}-1", "msg_type": "comm_open"},
        "content": {"comm_id": comm_id, "target_name": target, "data": data},
        "metadata": {"version": PROTOCOL},
        "buffers": buffers or [],
    }


def update_msg(
    comm_id: str, state: Dict[str, Any], *, with_header: bool = True
) -> Dict[str, Any]:
    msg: Dict[str, Any] = {
        "content": {
            "comm_id": comm_id,
            "data": {"method": "update", "state": state, "buffer_paths": []},
        },
        "buffers": [],
    }
    if with_header:
        msg["header"] = {"msg_id": f"{comm_id}-2", "msg_type": "comm_msg"}
    return msg


def close_msg(comm_id: str) -> Dict[str, Any]:
    return {
        "header": {"msg_id": f"{comm_id}-3", "msg_type": "comm_close"},
        "content": {"comm_id": comm_id, "data": {}},
        "buffers": [],
    }


@pytest.fixture
def primed(widget_session: Session) -> Session:
    """The session after its first widget: the comm manager and input effect exist.

    In a real app the comm_send effect is created in the same block, so a client
    message can never arrive before this; calling the handler directly can.
    """
    with session_context(widget_session):
        ipywidgets.IntSlider()
    flush()
    return widget_session


@pytest.fixture
def other_session() -> Any:
    """A second session, for cross-session cleanup tests."""
    session = App(ui.page_fluid(), widget_test_server)._create_session(MockConnection())
    try:
        yield session
    finally:
        asyncio.get_event_loop().run_until_complete(session.close())


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch) -> List[str]:
    """msg_type of every message ShinyComm would publish to the browser."""
    seen: List[str] = []
    original = ShinyComm._publish_msg

    def record(self: ShinyComm, msg_type: str, *args: Any, **kwargs: Any) -> None:
        seen.append(msg_type)
        original(self, msg_type, *args, **kwargs)

    monkeypatch.setattr(ShinyComm, "_publish_msg", record)
    return seen


def test_comm_open_constructs_widget_without_republishing(
    primed: Session, published: List[str]
) -> None:
    with session_context(primed):
        sw.handle_client_comm_msg(
            primed,
            open_msg("abc-1", model_state("IntSliderModel", "IntSliderView", value=5)),
        )
    w = WIDGET_INSTANCE_MAP["abc-1"]
    assert isinstance(w, ipywidgets.IntSlider)
    assert w.value == 5
    assert isinstance(w.comm, ShinyComm)
    assert sw.COMM_MANAGERS[primed.id].comms["abc-1"] is w.comm
    assert "abc-1" in sw.SESSION_WIDGET_ID_MAP[primed.id]
    assert "shinywidgets_comm_open" not in published
    flush()
    assert "shinywidgets_comm_open" not in published


def test_comm_msg_updates_browser_opened_widget(primed: Session) -> None:
    with session_context(primed):
        sw.handle_client_comm_msg(
            primed,
            open_msg("abc-2", model_state("IntSliderModel", "IntSliderView", value=5)),
        )
        sw.handle_client_comm_msg(primed, update_msg("abc-2", {"value": 9}))
    assert cast(ipywidgets.IntSlider, WIDGET_INSTANCE_MAP["abc-2"]).value == 9


def test_message_without_msg_type_is_an_update(primed: Session) -> None:
    with session_context(primed):
        w = ipywidgets.IntSlider()
    flush()
    with session_context(primed):
        sw.handle_client_comm_msg(
            primed, update_msg(w.model_id, {"value": 3}, with_header=False)
        )
    assert w.value == 3


def test_comm_close_closes_widget_without_republishing(
    primed: Session, published: List[str]
) -> None:
    with session_context(primed):
        sw.handle_client_comm_msg(
            primed, open_msg("abc-3", model_state("IntSliderModel", "IntSliderView"))
        )
        w = WIDGET_INSTANCE_MAP["abc-3"]
        sw.handle_client_comm_msg(primed, close_msg("abc-3"))
    assert is_closed_widget(w)
    assert "abc-3" not in WIDGET_INSTANCE_MAP
    assert "abc-3" not in sw.COMM_MANAGERS[primed.id].comms
    assert w.model_id == "abc-3"  # OrphanedShinyComm keeps the id readable
    assert "shinywidgets_comm_close" not in published


def test_comm_close_for_unknown_id_is_ignored(primed: Session) -> None:
    with session_context(primed):
        sw.handle_client_comm_msg(primed, close_msg("nope"))  # must not raise


def test_comm_open_for_registered_id_is_ignored(
    primed: Session, caplog: pytest.LogCaptureFixture
) -> None:
    with session_context(primed):
        w = ipywidgets.IntSlider(value=1)
    flush()
    with (
        caplog.at_level(logging.WARNING, logger="shinywidgets"),
        session_context(primed),
    ):
        sw.handle_client_comm_msg(
            primed,
            open_msg(
                w.model_id, model_state("IntSliderModel", "IntSliderView", value=7)
            ),
        )
    assert WIDGET_INSTANCE_MAP[w.model_id] is w
    assert w.value == 1
    assert any(w.model_id in r.getMessage() for r in caplog.records)


def test_comm_open_cannot_take_over_a_widget_not_yet_opened(
    primed: Session, caplog: pytest.LogCaptureFixture
) -> None:
    # Between construction and the flush that opens its comm, a Python widget is
    # in the global registry but not in the session's comm manager.
    with session_context(primed):
        w = ipywidgets.IntSlider(value=1)
    with (
        caplog.at_level(logging.WARNING, logger="shinywidgets"),
        session_context(primed),
    ):
        sw.handle_client_comm_msg(
            primed,
            open_msg(
                w.model_id, model_state("IntSliderModel", "IntSliderView", value=7)
            ),
        )
    assert WIDGET_INSTANCE_MAP[w.model_id] is w
    assert w.value == 1
    assert any(w.model_id in r.getMessage() for r in caplog.records)
    flush()
    assert isinstance(w.comm, ShinyComm)


def test_comm_open_for_other_target_is_ignored(
    primed: Session, caplog: pytest.LogCaptureFixture
) -> None:
    with (
        caplog.at_level(logging.WARNING, logger="shinywidgets"),
        session_context(primed),
    ):
        sw.handle_client_comm_msg(
            primed, open_msg("ctl-1", {}, target="jupyter.widget.control")
        )
    assert "ctl-1" not in WIDGET_INSTANCE_MAP
    assert "ctl-1" not in sw.COMM_MANAGERS[primed.id].comms
    assert any("jupyter.widget.control" in r.getMessage() for r in caplog.records)


def test_comm_open_for_unknown_model_logs_and_leaves_no_comm(
    primed: Session, caplog: pytest.LogCaptureFixture
) -> None:
    state = model_state("NoSuchModel", "NoSuchView")
    with caplog.at_level(logging.ERROR, logger="shinywidgets"), session_context(primed):
        sw.handle_client_comm_msg(primed, open_msg("bad-1", state))  # must not raise
    assert "bad-1" not in WIDGET_INSTANCE_MAP
    assert "bad-1" not in sw.COMM_MANAGERS[primed.id].comms
    assert any("bad-1" in r.getMessage() for r in caplog.records)


def test_comm_open_puts_buffers_into_state(primed: Session) -> None:
    png = b"\x89PNG\r\n\x1a\n"
    state = model_state("ImageModel", "ImageView", format="png")
    msg = open_msg(
        "img-1",
        state,
        buffer_paths=[["value"]],
        buffers=[base64.b64encode(png).decode("ascii")],
    )
    with session_context(primed):
        sw.handle_client_comm_msg(primed, msg)
    assert bytes(cast(ipywidgets.Image, WIDGET_INSTANCE_MAP["img-1"]).value) == png


def open_browser_model(
    session: Session,
    comm_id: str,
    model: str = "IntSliderModel",
    view: str = "IntSliderView",
    **traits: Any,
) -> ipywidgets.Widget:
    """Simulate the browser creating a model (e.g. pythreejs's light target)."""
    with session_context(session):
        sw.handle_client_comm_msg(
            session, open_msg(comm_id, model_state(model, view, **traits))
        )
    return cast(ipywidgets.Widget, WIDGET_INSTANCE_MAP[comm_id])


def name_from_browser(session: Session, referrer_id: str, *model_ids: str) -> None:
    """
    Simulate the browser pointing a container's `children` at models, the way
    pythreejs's light sends an update naming the target/shadow it just created.
    """
    children = [f"IPY_MODEL_{model_id}" for model_id in model_ids]
    with session_context(session):
        sw.handle_client_comm_msg(
            session, update_msg(referrer_id, {"children": children})
        )


def render_owned_box(session: Session) -> tuple[Context, ipywidgets.VBox]:
    """A container owned by a render (like the light), and that render's Context."""
    with session_context(session):
        ctx = Context()
        with ctx(), WidgetRenderContext():
            box = ipywidgets.VBox()
        flush()
    return ctx, box


def session_owned_box(session: Session) -> ipywidgets.VBox:
    with session_context(session), session_lifetime():
        box = ipywidgets.VBox()
    flush()
    return box


def invalidate(session: Session, ctx: Context) -> None:
    with session_context(session):
        ctx.invalidate()
        flush()


def test_browser_created_model_closes_with_the_render_that_named_it(
    primed: Session,
) -> None:
    """
    pythreejs's default DirectionalLight target/shadow: one set used to leak
    per re-render, living until the session ended.
    """
    ctx, parent = render_owned_box(primed)
    target = open_browser_model(primed, "target-1")
    name_from_browser(primed, parent.model_id, "target-1")
    assert parent.children == (target,)

    invalidate(primed, ctx)

    assert is_closed_widget(parent)
    assert is_closed_widget(target)
    assert "target-1" not in WIDGET_INSTANCE_MAP


def test_browser_created_model_named_by_an_already_closed_widget_is_closed(
    primed: Session,
) -> None:
    """
    During rapid re-renders the browser is still creating a render's models
    when the server retires that render, so the update naming them arrives
    after its widget closed. Nothing can ever reference them; close them then.
    """
    ctx, parent = render_owned_box(primed)
    parent_id = parent.model_id
    invalidate(primed, ctx)
    assert is_closed_widget(parent)

    target = open_browser_model(primed, "target-late")
    name_from_browser(primed, parent_id, "target-late")

    assert is_closed_widget(target)
    assert "target-late" not in WIDGET_INSTANCE_MAP


def test_models_named_in_a_browser_comm_open_close_with_their_referrer(
    primed: Session,
) -> None:
    """
    A browser-created model can name another in its own comm_open (pythreejs's
    light shadow names its camera): the whole chain closes together.
    """
    ctx, parent = render_owned_box(primed)
    camera = open_browser_model(primed, "camera-1")
    shadow = open_browser_model(
        primed, "shadow-1", "VBoxModel", "VBoxView", children=["IPY_MODEL_camera-1"]
    )
    name_from_browser(primed, parent.model_id, "shadow-1")

    invalidate(primed, ctx)

    assert is_closed_widget(shadow)
    assert is_closed_widget(camera)


def test_browser_created_model_nothing_has_named_yet_survives_invalidation(
    primed: Session,
) -> None:
    """
    The update attaching a new model to its parent is a separate message, so
    an invalidation can land in between: the model isn't garbage yet.
    """
    ctx, _ = render_owned_box(primed)
    target = open_browser_model(primed, "target-unnamed")

    invalidate(primed, ctx)

    assert not is_closed_widget(target)


def test_browser_created_model_survives_while_a_live_widget_references_it(
    primed: Session,
) -> None:
    keeper = session_owned_box(primed)
    ctx, parent = render_owned_box(primed)
    target = open_browser_model(primed, "target-2")
    name_from_browser(primed, parent.model_id, "target-2")
    keeper.children = (target,)

    invalidate(primed, ctx)

    assert is_closed_widget(parent)
    assert not is_closed_widget(target)


def test_browser_created_model_closes_once_its_last_live_reference_is_dropped(
    primed: Session,
) -> None:
    keeper = session_owned_box(primed)
    ctx, parent = render_owned_box(primed)
    target = open_browser_model(primed, "target-3")
    name_from_browser(primed, parent.model_id, "target-3")
    keeper.children = (target,)
    invalidate(primed, ctx)
    assert not is_closed_widget(target)

    keeper.children = ()
    unrelated_ctx, _ = render_owned_box(primed)
    invalidate(primed, unrelated_ctx)

    assert is_closed_widget(target)


def test_naming_a_browser_created_model_again_registers_it_once(
    primed: Session,
) -> None:
    """Otherwise every repeat of the update would grow the session's kept list."""
    _, parent = render_owned_box(primed)
    target = open_browser_model(primed, "target-twice")

    name_from_browser(primed, parent.model_id, "target-twice")
    name_from_browser(primed, parent.model_id, "target-twice")

    kept = sw.KEPT_WIDGETS.get(primed.id, [])
    assert [w for w in kept if w is target] == [target]


def test_python_created_widget_the_browser_names_keeps_its_own_lifetime(
    primed: Session,
) -> None:
    """Only browser-created models take their lifetime from what names them."""
    with session_context(primed), session_lifetime():
        slider = ipywidgets.IntSlider()
    flush()
    ctx, parent = render_owned_box(primed)
    name_from_browser(primed, parent.model_id, slider.model_id)
    assert parent.children == (slider,)

    invalidate(primed, ctx)

    assert is_closed_widget(parent)
    assert not is_closed_widget(slider)


def test_another_sessions_browser_cannot_close_a_browser_created_model(
    primed: Session, other_session: Session
) -> None:
    target = open_browser_model(primed, "target-x")
    ctx, parent = render_owned_box(other_session)
    name_from_browser(other_session, parent.model_id, "target-x")

    invalidate(other_session, ctx)

    assert is_closed_widget(parent)
    assert not is_closed_widget(target)


def test_browser_created_model_of_a_shared_widget_survives_invalidation(
    primed: Session, shared_state: None
) -> None:
    """
    A shared widget is never closed and isn't one of the session's own
    widgets, so the sweep can't see its references: what it names must not
    become a sweep candidate.
    """
    with shared_lifetime():
        scene = ipywidgets.VBox()
    with session_context(primed):
        sw.open_shared_in(scene, primed)
    target = open_browser_model(primed, "target-shared")
    name_from_browser(primed, scene.model_id, "target-shared")
    assert scene.children == (target,)

    ctx, _ = render_owned_box(primed)
    invalidate(primed, ctx)

    assert not is_closed_widget(target)


def test_model_named_where_the_sweep_cannot_follow_keeps_session_lifetime(
    primed: Session,
) -> None:
    """
    The sweep finds references through widget-valued traits. A name the
    referrer holds any other way (here, as a plain string) is invisible to
    it, so the model must not become a candidate it would wrongly close.
    """
    keeper = session_owned_box(primed)
    target = open_browser_model(primed, "target-str")
    with session_context(primed):
        sw.handle_client_comm_msg(
            primed,
            update_msg(keeper.model_id, {"_dom_classes": ["IPY_MODEL_target-str"]}),
        )
    assert keeper._dom_classes == ("IPY_MODEL_target-str",)

    ctx, _ = render_owned_box(primed)
    invalidate(primed, ctx)

    assert not is_closed_widget(target)
