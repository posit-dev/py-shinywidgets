import time

from ipywidgets import IntSlider
from shiny import reactive
from shiny.express import input, render, session, ui
from shinywidgets import reactive_read, render_widget

observer_calls = reactive.value(0)


@render_widget
def slider():
    s = IntSlider(value=0, max=100)

    # A slow handler makes messages pile up, so backpressure has something
    # to coalesce.
    def on_value(change: object) -> None:
        time.sleep(0.1)
        with reactive.isolate():
            observer_calls.set(observer_calls() + 1)

    s.observe(on_value, names="value")
    return s


@render.text
def model_id():
    return slider.widget.model_id


@render.text
def count():
    return str(observer_calls())


@render.text
def value():
    return str(reactive_read(slider.widget, "value"))


ui.input_action_button("bogus_ack", "bogus ack")


@reactive.effect
@reactive.event(input.bogus_ack)
async def _():
    await session.send_custom_message(
        "shinywidgets_comm_ack", {"comm_id": "nope", "msg_id": "nope-1"}
    )
