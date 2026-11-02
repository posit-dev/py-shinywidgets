"""
The browser can open a comm of its own (a widget's JavaScript creating a model,
e.g. bqplot's toolbar PanZoom or pythreejs light targets). Such a comm_open
constructs the Python counterpart through ipywidgets' own handler, so trait
references to the model resolve, and a comm_close from the browser closes it.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any, Dict, List, cast

import ipywidgets
import pytest
import shinywidgets._shinywidgets as sw
from shiny import Session, reactive
from shiny.session import session_context
from shinywidgets._comm import ShinyComm
from shinywidgets._render_widget_base import is_closed_widget
from shinywidgets._widget_registry import WIDGET_INSTANCE_MAP

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
    session: Session, comm_id: str, **traits: Any
) -> ipywidgets.Widget:
    """Simulate the browser creating a model (e.g. pythreejs's light target)."""
    with session_context(session):
        sw.handle_client_comm_msg(
            session,
            open_msg(comm_id, model_state("IntSliderModel", "IntSliderView", **traits)),
        )
    return cast(ipywidgets.Widget, WIDGET_INSTANCE_MAP[comm_id])


def test_render_invalidation_closes_browser_created_references(
    primed: Session,
) -> None:
    """
    Browser-created models (e.g. pythreejs's default DirectionalLight
    target/shadow) are session-owned, but exist only to back the state of the
    widget referencing them. When that widget's render is invalidated, they
    must close with it, not leak one set per re-render.
    """
    from ipywidgets import VBox
    from shiny.reactive._core import Context
    from shinywidgets._render_widget_base import WidgetRenderContext

    with session_context(primed):
        ctx = Context()
        with ctx(), WidgetRenderContext():
            parent = VBox()  # render-owned, like the light
        flush()

        target = open_browser_model(primed, "target-1")
        parent.children = (target,)  # like the light's `target` reference
        flush()
        assert not is_closed_widget(target)

        ctx.invalidate()
        flush()

    assert is_closed_widget(parent)
    assert is_closed_widget(target)
    assert "target-1" not in WIDGET_INSTANCE_MAP


def test_live_reference_keeps_a_browser_created_widget(primed: Session) -> None:
    """A browser-created widget another live widget references must survive."""
    from ipywidgets import VBox
    from shiny.reactive._core import Context
    from shinywidgets import session_lifetime
    from shinywidgets._render_widget_base import WidgetRenderContext

    with session_context(primed):
        with session_lifetime():
            keeper = VBox()

        ctx = Context()
        with ctx(), WidgetRenderContext():
            parent = VBox()
        flush()

        target = open_browser_model(primed, "target-2")
        parent.children = (target,)
        keeper.children = (target,)  # shared with a live widget
        flush()

        ctx.invalidate()
        flush()

        assert is_closed_widget(parent)
        assert not is_closed_widget(target)
