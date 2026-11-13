import ipywidgets as widgets
from shiny.express import render, ui
from shinywidgets import reactive_read, render_widget

ui.page_opts(title="Composing plain ipywidgets", fillable=True)

with ui.card():
    ui.card_header("A self-contained ipywidgets dashboard (interactive_output)")

    @render_widget
    def panel():
        x = widgets.IntSlider(description="x", min=0, max=20, value=4)
        y = widgets.IntSlider(description="y", min=0, max=20, value=6)
        out = widgets.Label()

        def show_sum(*_):
            out.value = f"x + y = {x.value + y.value}"

        for w in (x, y):
            w.observe(show_sum, "value")
        show_sum()

        return widgets.VBox([x, y, out])

with ui.card():
    ui.card_header("Shiny still sees inside it: reactive_read() on a child widget")

    @render.code
    def x_value():
        x = panel.widget.children[0]
        return f"x.value = {reactive_read(x, 'value')}"
