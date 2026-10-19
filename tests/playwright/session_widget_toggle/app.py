# A session-owned widget (constructed once per session, outside any render)
# whose only output is repeatedly removed/re-added by render.ui.
import ipywidgets as W
from shiny import App, render, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fluid(
    ui.input_checkbox("show", "Show", True),
    ui.output_ui("panel"),
    # A static (always-present) output_widget so output.js's dependencies load
    # with the initial page rather than with render.ui's HTML -- otherwise a
    # comm_open for a render.ui-only widget can arrive before output.js has
    # registered its message handler and gets silently dropped (a pre-existing,
    # unrelated bug, out of scope here).
    ui.div(output_widget("unused"), style="display: none;"),
)


def server(input, output, session):
    held = W.IntSlider(description="held")

    @render.ui
    def panel():
        return output_widget("w") if input.show() else ui.p("hidden")

    @render_widget
    def w():
        return held

    @render_widget
    def unused():
        return W.HTML(value="unused")


app = App(app_ui, server)
