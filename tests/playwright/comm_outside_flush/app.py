# Widgets updated with no client input: one from an asyncio task, one from a
# thread. Each update carries the server time it was sent at, so the test can
# measure delivery latency.
from __future__ import annotations

import asyncio
import threading
import time

import ipywidgets as widgets
from shiny import App, ui
from shinywidgets import output_widget, render_widget

INTERVAL = 0.1

app_ui = ui.page_fluid(
    output_widget("from_task", fill=False),
    output_widget("from_thread", fill=False),
)


def stamp(n: int) -> str:
    return f"{n} {time.time() * 1000:.0f}"


def server(input, output, session):
    task_label = widgets.Label(value="waiting")
    thread_label = widgets.Label(value="waiting")

    async def tick_from_task() -> None:
        n = 0
        while True:
            await asyncio.sleep(INTERVAL)
            n += 1
            task_label.value = stamp(n)

    stop = threading.Event()

    def tick_from_thread() -> None:
        n = 0
        while not stop.wait(INTERVAL):
            n += 1
            thread_label.value = stamp(n)

    task = asyncio.create_task(tick_from_task())
    threading.Thread(target=tick_from_thread, daemon=True).start()

    session.on_ended(task.cancel)
    session.on_ended(stop.set)

    @render_widget
    def from_task():
        return task_label

    @render_widget
    def from_thread():
        return thread_label


app = App(app_ui, server)
