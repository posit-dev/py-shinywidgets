# Repro: a second, unrelated @render_holoviews output in the same session
# silently breaks link_selections box-select on the FIRST output (no error,
# no selection, selection_expr never updates) -- verified via the server-side
# reactive value, not just visually. A single render_holoviews output with
# the exact same link_selections code works fine (see
# gallery/template_crossfilter.py in the guide dir).
import holoviews as hv
import hvplot.pandas  # noqa: F401
import numpy as np
import pandas as pd
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_holoviews

hv.extension("bokeh")
ui.page_opts(fillable=True)

rng = np.random.default_rng(0)
df = pd.DataFrame({"x": rng.normal(size=200), "y": rng.normal(size=200)})

links = hv.link_selections.instance()
sel = reactive.value(None)
_w = links.param.watch(lambda e: sel.set(e.new), "selection_expr")

with ui.layout_columns():
    with ui.card():
        @render_holoviews
        def linked():
            a = df.hvplot.scatter("x", "y", responsive=True, title="A")
            b = df.hvplot.hist("x", responsive=True, title="B")
            return links(a + b)

    with ui.card():
        @render_holoviews
        def other():
            return df.hvplot.scatter("x", "y", responsive=True, title="C")

@render.text
def sel_text():
    # Box-select on "A", then check: this never changes from "True".
    return f"selection_expr is None: {sel() is None}"
