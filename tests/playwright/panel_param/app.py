from __future__ import annotations

import panel as pn
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_panel

ui.input_action_button("bump", "Bump from Python")


@render_panel
def slider():
    return pn.widgets.IntSlider(value=5, start=0, end=10)


@render.text
def value():
    return str(slider.param("value"))


@reactive.effect
@reactive.event(input.bump)
def _():
    slider.value.value = 9
