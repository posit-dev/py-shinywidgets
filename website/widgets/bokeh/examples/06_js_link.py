import numpy as np
from bokeh.layouts import column
from bokeh.models import CustomJS, Slider
from bokeh.plotting import figure
from shiny.express import ui
from shinywidgets import render_bokeh

ui.page_opts(title="Client-only interactivity", fillable=True)

x = np.linspace(0, 4 * np.pi, 400)

with ui.card(full_screen=True):
    ui.card_header("Drag the slider: no round trip to Python")

    @render_bokeh
    def plot():
        p = figure(sizing_mode="stretch_both")
        line = p.line(x, np.sin(x), line_width=3)

        slider = Slider(start=0.1, end=5, value=1, step=0.1, title="frequency")
        slider.js_on_change(
            "value",
            CustomJS(
                args=dict(source=line.data_source, freq=slider),
                code="""
                const data = source.data
                const x = data['x']
                const y = data['y']
                for (let i = 0; i < x.length; i++) {
                    y[i] = Math.sin(freq.value * x[i])
                }
                source.change.emit()
                """,
            ),
        )
        return column(slider, p, sizing_mode="stretch_both")
