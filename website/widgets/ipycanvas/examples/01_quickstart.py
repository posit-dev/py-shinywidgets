from ipycanvas import Canvas
from shiny.express import ui
from shinywidgets import render_ipycanvas

ui.page_opts(title="ipycanvas quickstart", fillable=True)

with ui.card(full_screen=True):

    @render_ipycanvas
    def canvas():
        c = Canvas(width=400, height=250)
        c.fill_style = "#f4f1ea"
        c.fill_rect(0, 0, 400, 250)
        c.fill_style = "steelblue"
        c.fill_rect(20, 20, 140, 90)
        c.fill_style = "#e67e22"
        c.fill_circle(260, 90, 55)
        c.font = "20px sans-serif"
        c.fill_style = "#222"
        c.fill_text("Hello from Python", 20, 160)
        return c
