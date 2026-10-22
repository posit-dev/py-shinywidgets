"""
Exceptions raised by widget callbacks while handling a browser message are
caught by ipywidgets and logged to the `traitlets` logger, whose only handler is
a NullHandler, so outside of IPython they would vanish. shinywidgets re-routes
them to its own logger so they show up in the server's console.
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
from shinywidgets._comm import ShinyComm


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


def test_unrelated_thread_logging_stays_suppressed_during_dispatch(
    widget_session: Session,
) -> None:
    # Lowering the traitlets level during dispatch is process-wide, so
    # warnings logged by threads outside the dispatch must keep honoring the
    # threshold that applied before the dispatch (here, a root logger at
    # ERROR). caplog can't observe this (its handler level is raised too), so
    # attach a level-NOTSET handler directly.
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

    # The WARNING stays suppressed (as before/after dispatch); the ERROR
    # passes, just as it would without a dispatch in progress.
    assert [(r.name, r.levelno) for r in records] == [("traitlets", logging.ERROR)]


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
