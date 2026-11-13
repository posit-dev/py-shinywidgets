# Repro: a hv.streams.Tap attached to an element that is ALSO passed through
# hv.link_selections() never fires (tap_xy stays None forever), even though
# the tap-select tool is present in the toolbar. Attach Tap to a separate,
# unlinked plot instead (see guide examples/08_tap_detail.py).
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
tap_xy = reactive.value(None)


@render_holoviews
def linked():
    a = df.hvplot.scatter("x", "y", responsive=True, title="A", tools=["tap"])
    b = df.hvplot.hist("x", responsive=True, title="B")
    hv.streams.Tap(source=a).add_subscriber(lambda x, y: tap_xy.set((x, y)))
    return links(a + b)


@render.text
def tap_text():
    return str(tap_xy())
