from __future__ import annotations
import numpy as np, pandas as pd
from mosaic_widget import MosaicWidget
from shiny import App, ui
from shinywidgets import output_widget, render_widget, reactive_read

rng = np.random.default_rng(0)
df = pd.DataFrame({"x": rng.normal(size=500), "y": rng.normal(size=500)})
spec = {
  "params": {"brush": {"select": "crossfilter"}},
  "vconcat": [
    {"plot": [{"mark": "dot", "data": {"from": "pts", "filter": "$brush"}, "x": "x", "y": "y"},
              {"select": "intervalXY", "as": "$brush"}], "width": 400, "height": 200},
    {"plot": [{"mark": "rectY", "data": {"from": "pts", "filter": "$brush"}, "x": {"bin": "x"}, "y": {"count": ""}}],
     "width": 400, "height": 150},
  ],
}
app_ui = ui.page_fillable(
    ui.card(output_widget("m"), style="height:600px"),
    ui.output_text("p"),
)
def server(input, output, session):
    @render_widget
    def m():
        return MosaicWidget(spec, data={"pts": df})
    from shiny import render
    @render.text
    def p():
        return str(reactive_read(m.widget, "params"))
app = App(app_ui, server)
