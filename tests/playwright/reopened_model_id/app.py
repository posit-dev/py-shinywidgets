# A rendered widget with an explicitly assigned (and reused) model id: each
# re-render closes the previous widget and opens a new one with the same
# comm id.
import ipywidgets as W
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    output_widget("slider"),
)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_widget
    def slider():
        return W.IntSlider(
            description=f"render {counter.get()}",
            model_id="explicit-slider-id",
        )


app = App(app_ui, server)
