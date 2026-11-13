from ipycanvas import RoughCanvas
from shiny.express import input, ui
from shinywidgets import render_ipycanvas

ui.page_opts(title="RoughCanvas", fillable=True)

with ui.card(full_screen=True):
    ui.input_select(
        "style", "Fill style", ["hachure", "cross-hatch", "zigzag", "dots", "solid"]
    )

    @render_ipycanvas
    def sketch():
        c = RoughCanvas(width=420, height=220)
        c.rough_fill_style = input.style()
        c.fill_style = "#2c7fb8"
        c.fill_rect(20, 20, 160, 120)
        c.fill_style = "#e67e22"
        c.fill_circle(320, 80, 60)
        c.stroke_style = "#333"
        c.stroke_line(20, 180, 400, 180)
        return c
