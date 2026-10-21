from __future__ import annotations

import numpy as np
import pandas as pd
from embedding_atlas.widget import EmbeddingAtlasWidget
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_embedding_atlas

rng = np.random.default_rng(0)
N = 300
docs = pd.DataFrame(
    {
        "x": rng.normal(size=N),
        "y": rng.normal(size=N),
        "text": [f"item {i}" for i in range(N)],
        "group": rng.choice(["a", "b", "c"], size=N),
    }
)

app_ui = ui.page_fillable(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.output_text("selection_size"),
    ui.card(
        ui.card_header("Embedding Atlas in a fillable card"),
        output_widget("atlas"),
        full_screen=True,
    ),
)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_embedding_atlas
    def atlas():
        counter.get()
        return EmbeddingAtlasWidget(docs, x="x", y="y", text="text")

    @render.text
    def selection_size():
        # `_predicate` is the SQL filter the browser syncs when the user
        # selects/filters points (upstream-internal, but the only selection state
        # the widget syncs); selection() applies it to the data
        reactive_read(atlas.widget, "_predicate")
        return str(len(atlas.widget.selection()))


app = App(app_ui, server)
