import ipyvolume as ipv
import numpy as np
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_ipyvolume

app_ui = ui.page_fillable(
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_slider("n", "Number of points", 100, 50000, 3000, step=100),
            ui.p(
                "Drag to orbit; scroll to zoom. Hold Ctrl and drag to select "
                "points with the rectangle selector.",
                class_="text-muted small",
            ),
            ui.output_text("selected"),
            width=300,
        ),
        ui.card(
            ui.card_header("3D scatter (ipyvolume)"),
            output_widget("plot"),
            full_screen=True,
        ),
    ),
)


def server(input, output, session):
    selection = reactive.value("No selection yet")

    @render_ipyvolume
    def plot():
        rng = np.random.default_rng(0)
        x, y, z = rng.normal(size=(3, input.n()))
        ipv.quickscatter(x, y, z, size=2, marker="sphere", color="tomato")
        fig = ipv.gcf()
        fig.selector = "rectangle"
        # Selections arrive as custom messages (not trait changes), so read
        # them in a callback and set a reactive value
        fig.on_selection(
            lambda data: selection.set(
                f"{data['type']} selection, pixel region "
                f"{data['pixel']['begin']} -> {data['pixel']['end']}"
            )
        )
        return fig

    @render.text
    def selected():
        return selection.get()


app = App(app_ui, server)
