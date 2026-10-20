import ipywidgets as W
from shiny import App, reactive, ui
from shinywidgets import output_widget, render_widget, session_lifetime

# A mistake that's easy to make when trying to avoid rebuilding an expensive
# widget per visitor: caching it at module scope (shared by every session)
# instead of per session.
CACHE: dict[str, W.IntSlider] = {}

app_ui = ui.page_fluid(
    ui.input_action_button("bump", "Bump value"),
    output_widget("direct"),
    output_widget("as_child"),
)


def server(input, output, session):
    @render_widget
    def direct():
        if "chart" not in CACHE:
            with session_lifetime():
                CACHE["chart"] = W.IntSlider(description="cached", value=0)
        return CACHE["chart"]

    @render_widget
    def as_child():
        if "chart" not in CACHE:
            return None
        return W.VBox([W.Label("child"), CACHE["chart"]])

    @reactive.effect
    @reactive.event(input.bump)
    def _():
        CACHE["chart"].value += 1


app = App(app_ui, server)
