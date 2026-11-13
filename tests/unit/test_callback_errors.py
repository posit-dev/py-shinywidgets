"""
Exceptions raised by widget callbacks while handling a browser message are
caught by ipywidgets and logged to the `traitlets` logger, whose only handler is
a NullHandler, so outside of IPython they would vanish. shinywidgets re-routes
them to its own logger so they show up in the server's console, and shows the
user a sticky error notification (one per widget), since the error usually
means their output is blank.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Dict, List

import pytest
from ipywidgets import Button, IntSlider
from shiny import Session, reactive
from shiny.session import session_context
from shinywidgets._comm import ClientMsgScope, ShinyComm, handling_client_msg


def flush() -> None:
    asyncio.get_event_loop().run_until_complete(reactive.flush())


def client_msg(comm_id: str, data: Dict[str, Any]) -> Dict[str, object]:
    return {"content": {"comm_id": comm_id, "data": data}, "buffers": []}


def open_comm(widget: Any) -> ShinyComm:
    flush()
    assert isinstance(widget.comm, ShinyComm)
    return widget.comm


def test_observer_error_from_browser_update_is_logged(
    widget_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    def boom(change: object) -> None:
        raise RuntimeError("observer failed")

    with session_context(widget_session):
        slider = IntSlider(value=1)
        slider.observe(boom, names="value")
        comm = open_comm(slider)
        with caplog.at_level(logging.WARNING):
            comm.handle_msg(
                client_msg(
                    comm.comm_id,
                    {"method": "update", "state": {"value": 5}, "buffer_paths": []},
                )
            )

    [record] = caplog.records
    assert record.name == "shinywidgets"
    assert record.levelno == logging.ERROR
    assert record.exc_info is not None
    assert isinstance(record.exc_info[1], RuntimeError)
    assert "observer failed" in caplog.text


def test_callback_dispatcher_error_from_browser_event_is_logged(
    widget_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    def boom(button: Button) -> None:
        raise ValueError("click handler failed")

    with session_context(widget_session):
        button = Button()
        button.on_click(boom)
        comm = open_comm(button)
        with caplog.at_level(logging.WARNING):
            comm.handle_msg(
                client_msg(
                    comm.comm_id,
                    {"method": "custom", "content": {"event": "click"}},
                )
            )

    [record] = caplog.records
    assert record.name == "shinywidgets"
    assert record.exc_info is not None
    assert isinstance(record.exc_info[1], ValueError)


def test_traitlets_logging_outside_browser_messages_is_untouched(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        logging.getLogger("traitlets").warning("unrelated")

    [record] = caplog.records
    assert record.name == "traitlets"


def test_callback_error_is_logged_when_root_logger_is_at_error(
    widget_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    # Logger filters only run after the level check, so with the root logger
    # at ERROR the WARNING record would never reach the rerouting filter.
    def boom(change: object) -> None:
        raise RuntimeError("observer failed")

    with session_context(widget_session):
        slider = IntSlider(value=1)
        slider.observe(boom, names="value")
        comm = open_comm(slider)
        with caplog.at_level(logging.ERROR):
            comm.handle_msg(
                client_msg(
                    comm.comm_id,
                    {"method": "update", "state": {"value": 5}, "buffer_paths": []},
                )
            )

    [record] = caplog.records
    assert record.name == "shinywidgets"
    assert record.levelno == logging.ERROR
    assert record.exc_info is not None
    assert isinstance(record.exc_info[1], RuntimeError)


def test_logging_outside_the_dispatch_is_untouched_during_dispatch(
    widget_session: Session,
) -> None:
    # Admitting callback records during dispatch must not change the
    # threshold for records logged outside it: other threads, and descendant
    # loggers (whose records bypass the traitlets logger's filters). Here the
    # root logger is at ERROR. caplog can't observe this (its handler level
    # is raised too), so attach a level-NOTSET handler directly.
    records: List[logging.LogRecord] = []

    class ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    in_dispatch = threading.Event()
    logged = threading.Event()

    def wait(change: object) -> None:
        in_dispatch.set()
        assert logged.wait(10)

    def worker() -> None:
        assert in_dispatch.wait(10)
        logging.getLogger("traitlets").warning("unrelated warning")
        logging.getLogger("traitlets").error("unrelated error")
        logging.getLogger("traitlets.worker").warning("descendant warning")
        logging.getLogger("traitlets.worker").error("descendant error")
        logged.set()

    root = logging.getLogger()
    prev_level = root.level
    handler = ListHandler()
    root.addHandler(handler)
    root.setLevel(logging.ERROR)
    try:
        with session_context(widget_session):
            slider = IntSlider(value=1)
            slider.observe(wait, names="value")
            comm = open_comm(slider)
            thread = threading.Thread(target=worker)
            thread.start()
            comm.handle_msg(
                client_msg(
                    comm.comm_id,
                    {"method": "update", "state": {"value": 5}, "buffer_paths": []},
                )
            )
            thread.join(10)
    finally:
        root.removeHandler(handler)
        root.setLevel(prev_level)

    # The WARNINGs stay suppressed (as before/after dispatch); the ERRORs
    # pass, just as they would without a dispatch in progress.
    assert [(r.name, r.levelno) for r in records] == [
        ("traitlets", logging.ERROR),
        ("traitlets.worker", logging.ERROR),
    ]


def test_deferred_work_after_dispatch_keeps_traitlets_logging(
    widget_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    # asyncio tasks copy the current context, so a task scheduled by a widget
    # callback inherits the dispatch context. Once dispatch ends, its
    # traitlets logging must go back to normal.
    async def deferred() -> None:
        logging.getLogger("traitlets").warning("deferred warning")

    def schedule(change: object) -> None:
        asyncio.get_event_loop().create_task(deferred())

    with session_context(widget_session):
        slider = IntSlider(value=1)
        slider.observe(schedule, names="value")
        comm = open_comm(slider)
        with caplog.at_level(logging.WARNING):
            comm.handle_msg(
                client_msg(
                    comm.comm_id,
                    {"method": "update", "state": {"value": 5}, "buffer_paths": []},
                )
            )
            asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.1))

    [record] = caplog.records
    assert record.name == "traitlets"
    assert record.levelno == logging.WARNING


def test_scope_keeps_error_messages_not_exceptions(widget_session: Session) -> None:
    # Deferred work (asyncio tasks, loop.call_soon) shares the dispatch scope
    # via its copied context, so an exception kept on it would keep its
    # traceback's frames -- and through them the widget, its callbacks and
    # session -- alive for the lifetime of that work, even after the widget
    # is closed or replaced.
    scopes: List[ClientMsgScope] = []

    def boom(change: object) -> None:
        scope = handling_client_msg.get()
        assert scope is not None
        scopes.append(scope)
        raise RuntimeError("observer failed")

    with session_context(widget_session):
        slider = IntSlider(value=1)
        slider.observe(boom, names="value")
        comm = open_comm(slider)
        comm.handle_msg(
            client_msg(
                comm.comm_id,
                {"method": "update", "state": {"value": 5}, "buffer_paths": []},
            )
        )

    [scope] = scopes
    assert scope.errors == ["observer failed"]


def capture_notifications(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> List[Dict[str, Any]]:
    sent: List[Dict[str, Any]] = []
    monkeypatch.setattr(session, "_send_message_sync", sent.append)
    return sent


def failing_slider() -> ShinyComm:
    def boom(change: object) -> None:
        raise RuntimeError("observer failed")

    slider = IntSlider(value=1)
    slider.observe(boom, names="value")
    comm = open_comm(slider)
    comm.handle_msg(
        client_msg(
            comm.comm_id,
            {"method": "update", "state": {"value": 5}, "buffer_paths": []},
        )
    )
    return comm


def test_observer_error_notifies_browser(
    widget_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sent = capture_notifications(widget_session, monkeypatch)
    with session_context(widget_session), caplog.at_level(logging.WARNING):
        failing_slider()

    # Still logged server-side (the #304 behavior) ...
    [record] = caplog.records
    assert record.name == "shinywidgets"
    # ... and now also shown to the user as a sticky error notification.
    [note] = [m for m in sent if "notification" in m]
    payload = note["notification"]["message"]
    assert payload["type"] == "error"
    assert payload["duration"] is None
    assert "observer failed" in payload["html"]


def test_repeat_errors_reuse_the_widgets_notification(
    widget_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sent = capture_notifications(widget_session, monkeypatch)
    with session_context(widget_session), caplog.at_level(logging.WARNING):
        comm = failing_slider()
        comm.handle_msg(
            client_msg(
                comm.comm_id,
                {"method": "update", "state": {"value": 6}, "buffer_paths": []},
            )
        )
        other = failing_slider()

    # Every failure is logged ...
    assert len(caplog.records) == 3
    # ... but the browser replaces a notification whose id it already shows,
    # so an observer that fails on every message leaves one per widget.
    ids = [m["notification"]["message"]["id"] for m in sent if "notification" in m]
    assert ids == [
        f"shinywidgets-error-{comm.comm_id}",
        f"shinywidgets-error-{comm.comm_id}",
        f"shinywidgets-error-{other.comm_id}",
    ]


def test_warning_without_exception_does_not_notify(
    widget_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def warn(change: object) -> None:
        logging.getLogger("traitlets").warning("heads up")

    sent = capture_notifications(widget_session, monkeypatch)
    with session_context(widget_session), caplog.at_level(logging.WARNING):
        slider = IntSlider(value=1)
        slider.observe(warn, names="value")
        comm = open_comm(slider)
        comm.handle_msg(
            client_msg(
                comm.comm_id,
                {"method": "update", "state": {"value": 5}, "buffer_paths": []},
            )
        )

    assert "heads up" in caplog.text
    assert [m for m in sent if "notification" in m] == []


def test_observer_error_notification_sanitized_when_app_sanitizes(
    widget_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    widget_session.app.sanitize_errors = True
    sent = capture_notifications(widget_session, monkeypatch)
    with session_context(widget_session), caplog.at_level(logging.WARNING):
        failing_slider()

    [note] = [m for m in sent if "notification" in m]
    assert note["notification"]["message"]["html"] == (
        "An error has occurred. Check your logs or contact the app author for clarification."
    )
