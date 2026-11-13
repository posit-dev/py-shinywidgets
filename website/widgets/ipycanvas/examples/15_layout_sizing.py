from ipycanvas import Canvas
from shiny.express import ui
from shinywidgets import render_ipycanvas

ui.page_opts(title="Layout and sizing", fillable=True)


def draw(c: Canvas) -> Canvas:
    c.fill_style = "#f4f1ea"
    c.fill_rect(0, 0, c.width, c.height)
    c.fill_style = "steelblue"
    c.fill_circle(c.width / 2, c.height / 2, min(c.width, c.height) / 2 - 10)
    return c


with ui.layout_columns(col_widths=(4, 4, 4)):
    with ui.card(full_screen=True):
        ui.card_header("Default: fills, centers, keeps buffer size")

        @render_ipycanvas
        def fill_card():
            return draw(Canvas(width=300, height=200))

    with ui.card(full_screen=True):
        ui.card_header("output height=150px: shrinks to fit, aspect kept")

        @render_ipycanvas(height="150px")
        def fixed_height():
            return draw(Canvas(width=300, height=200))

    with ui.card(full_screen=True):
        ui.card_header("widget.layout.height set: don't do this")

        @render_ipycanvas
        def layout_height_trap():
            c = draw(Canvas(width=300, height=200))
            c.layout.height = "120px"  # opts out of fill AND stretches the bitmap
            return c
