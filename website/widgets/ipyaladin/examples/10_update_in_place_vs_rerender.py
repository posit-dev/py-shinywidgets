from ipyaladin import Aladin
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipyaladin

ui.page_opts(title="Update in place vs. re-render", fillable=True)
ui.input_action_button("rerender", "Re-render (new Aladin())")
ui.input_action_button("in_place", "Update in place (.widget.target = ...)")
ui.p(
    "Zoom the sky to some custom field of view first, then try each button: "
    "in-place keeps it, re-render resets it to the constructor's fov=1.",
    class_="text-muted",
)

with ui.card(full_screen=True):

    @render_ipyaladin
    @reactive.event(input.rerender, ignore_none=False)
    def sky():
        return Aladin(target=(83.822, -5.391), fov=1)  # M42

    @reactive.effect
    @reactive.event(input.in_place)
    def _():
        sky.widget.target = "10.685 41.269"  # M31

    @render.text
    def fov():
        return f"field of view: {sky.fov().deg:.3f} deg"
