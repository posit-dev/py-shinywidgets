import numpy as np
import pandas as pd
from astropy.table import Table
from ipyaladin import Aladin
from jscatter import Scatter
from shiny import reactive
from shiny.express import ui
from shinywidgets import render_ipyaladin, render_jscatter

# A plausible color-magnitude diagram for ~400 field stars around the
# Pleiades (synthetic: real surveys of this field have far more stars than
# fit cleanly in a short demo, but the main-sequence shape is realistic)
rng = np.random.default_rng(0)
n = 400
bp_rp = rng.uniform(-0.3, 2.5, n)
abs_g = -(4.5 * bp_rp + rng.normal(0, 0.6, n) + 1.0)
stars = pd.DataFrame(
    {
        "ra": 56.75 + rng.normal(0, 0.6, n),
        "dec": 24.12 + rng.normal(0, 0.5, n),
        "bp_rp": bp_rp,
        "abs_g": abs_g,
    }
)

ui.page_opts(title="Select stars in a plot, mark them on the sky", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Color-magnitude diagram (lasso to select)")

        @render_jscatter
        def hr():
            return Scatter(data=stars, x="bp_rp", y="abs_g").lasso(initiator=True)

    with ui.card(full_screen=True):
        ui.card_header("Selected stars on the sky")

        @render_ipyaladin
        def sky():
            return Aladin(target=(56.75, 24.12), fov=2)


@reactive.effect
def _mark_selection():
    w = sky.widget
    idx = hr.selected()
    if w is None:
        return
    with reactive.isolate():
        try:
            w.remove_overlay("selected")
        except ValueError:
            pass
        if len(idx):
            w.add_table(
                Table.from_pandas(stars.iloc[idx]),
                name="selected",
                color="#ef476f",
                shape="circle",
                source_size=12,
            )
