from ipywidgets import IntSlider
from shiny.express import render, ui
from shinywidgets import render_widget

ui.page_opts(title="render_widget quick start", fillable=True)

with ui.card():
    ui.card_header("Any ipywidgets.Widget subclass works, no coercion needed")

    @render_widget
    def slider():
        return IntSlider(value=7, min=0, max=10, description="Threshold:")

    @render.code
    def slider_val():
        return f"slider.read('value') = {slider.read('value')}"
