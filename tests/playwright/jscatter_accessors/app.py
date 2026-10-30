from __future__ import annotations

import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny import App, render, ui
from shinywidgets import output_widget, render_jscatter

rng = np.random.default_rng(0)
N = 200
df = pd.DataFrame({"x": rng.uniform(0, 1, N), "y": rng.uniform(0, 1, N)})

app_ui = ui.page_fluid(
    output_widget("sc", height="400px"),
    ui.output_text("sel"),
)


def server(input, output, session):
    @render_jscatter
    def sc():
        return Scatter(data=df, x="x", y="y")

    @render.text
    def sel():
        return ",".join(str(i) for i in sc.selection())


app = App(app_ui, server)
