from ipycanvas import MultiCanvas
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_ipycanvas

ui.page_opts(title="MultiCanvas layers", fillable=True)

W, H = 420, 280

with ui.card(full_screen=True):
    ui.input_action_button("clear", "Clear sketch (grid stays)", class_="mb-2")

    @render_ipycanvas
    def mc():
        canvas = MultiCanvas(2, width=W, height=H)
        grid, ink = canvas[0], canvas[1]

        # Layer 0: a dot grid, drawn once -- it's never touched again
        grid.fill_style = "#ccc"
        for x in range(10, W, 20):
            for y in range(10, H, 20):
                grid.fill_circle(x, y, 1.2)

        # Layer 1: a few "sticky note" shapes
        ink.fill_style = "#f1c40f"
        ink.fill_rect(40, 40, 90, 90)
        ink.fill_style = "#e74c3c"
        ink.fill_rect(160, 90, 90, 90)
        ink.fill_style = "#2ecc71"
        ink.fill_rect(260, 50, 90, 90)
        return canvas

    @reactive.effect
    @reactive.event(input.clear)
    def _():
        canvas = mc.widget
        if canvas is not None:
            canvas[1].clear()  # only the ink layer is erased
