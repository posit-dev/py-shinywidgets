import asyncio
import json

import ipywidgets
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fluid(
    ui.output_text("values"),
    ui.output_text("acks"),
    output_widget("widget"),
)


def server(input, output, session):
    received_values = reactive.value([])
    acked_events = reactive.value([])

    @reactive.effect
    @reactive.event(input.lifecycle_probe)
    async def _():
        packet = input.lifecycle_probe()
        received_values.set(received_values.get() + [packet])
        # Respond through a custom message; this must be deliverable even
        # while widget initialization is still pending.
        for event in packet["events"]:
            acked_events.set(acked_events.get() + [event])
            await session.send_custom_message(
                "lifecycle_probe_ack",
                json.dumps({"ack": event}),
            )

    @render.text
    def values():
        return ",".join(str(v) for v in received_values.get())

    @render.text
    def acks():
        return ",".join(str(a) for a in acked_events.get())

    @render_widget
    async def widget():
        # A widget whose initialization stays pending for a while.
        await asyncio.sleep(0.5)
        return ipywidgets.HTML("slow widget")


app = App(app_ui, server)
