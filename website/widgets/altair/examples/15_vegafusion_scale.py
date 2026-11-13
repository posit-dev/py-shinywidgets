import altair as alt
import numpy as np
import pandas as pd
from shiny.express import render, ui

from shinywidgets import render_altair

# Above ~5,000 rows, Altair raises MaxRowsError on a bare DataFrame unless you
# opt into a transformer that stops inlining raw rows into the spec. VegaFusion
# computes bin/aggregate transforms in Python (via DataFusion) instead of the
# browser, so only the aggregated result crosses the wire -- not the million
# rows behind it. Assign the return value: Shiny Express auto-displays any
# bare top-level expression, including the enabler object `enable()` returns.
_ = alt.data_transformers.enable("vegafusion")

rng = np.random.default_rng(0)
n = 1_000_000
df = pd.DataFrame({"value": rng.normal(loc=50, scale=15, size=n)})

ui.page_opts(title="VegaFusion at scale", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header(f"Click a bar ({n:,} rows, aggregated with VegaFusion)")

        @render_altair
        def histogram():
            pick = alt.selection_point(name="bin", encodings=["x"])
            return (
                alt.Chart(df)
                .mark_bar()
                .encode(x=alt.X("value:Q", bin=alt.Bin(maxbins=40)), y="count()")
                .add_params(pick)
            )

    with ui.card(full_screen=True):
        ui.card_header("histogram.selected_rows('bin')")

        @render.code
        def count():
            rows = histogram.selected_rows("bin")
            return f"{len(rows):,} of {len(df):,} rows in the selected bin"
