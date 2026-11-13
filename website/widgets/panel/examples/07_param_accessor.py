import panel as pn
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_panel

ui.page_opts(title="param(name): read a Panel parameter like an input", fillable=True)

with ui.layout_columns(col_widths=[6, 6]):
    with ui.card():
        ui.card_header("Drag the slider, or bump it from Python")
        ui.input_action_button("bump", "+2 from Python")

        @render_panel
        def slider():
            return pn.widgets.IntSlider(name="Quantity", value=5, start=0, end=20)

    with ui.card():
        ui.card_header("slider.param('value') -- reads both kinds of change")

        @render.text
        def value():
            return f"quantity = {slider.param('value')}"


@reactive.effect
@reactive.event(input.bump)
def _():
    slider.value.value += 2
