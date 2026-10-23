from __future__ import annotations

import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny import App, ui
from shinywidgets import output_widget, render_embedding_atlas

app_ui = ui.page_fluid(
    output_widget("output_height", height="320px"),
    output_widget("widget_height"),
)


def make_widget() -> EmbeddingAtlasWidget:
    df = pd.DataFrame({"x": [0.0, 1.0, 2.0], "y": [2.0, 1.0, 0.0], "text": list("abc")})
    return EmbeddingAtlasWidget(df, x="x", y="y", text="text")


def server(input, output, session):
    @render_embedding_atlas
    def output_height():
        return make_widget()

    @render_embedding_atlas
    def widget_height():
        w = make_widget()
        w.layout.height = "360px"
        return w


app = App(app_ui, server)
