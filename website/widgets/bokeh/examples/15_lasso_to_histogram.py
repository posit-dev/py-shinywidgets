import matplotlib.pyplot as plt
import numpy as np
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from shiny.express import render, ui
from shinywidgets import render_bokeh, render_matplotlib

ui.page_opts(title="Bokeh selection -> matplotlib histogram", fillable=True)

rng = np.random.default_rng(6)
src = ColumnDataSource({"x": rng.normal(size=400), "y": rng.normal(size=400)})

with ui.layout_columns():
    with ui.card(full_screen=True):

        @render_bokeh
        def scatter():
            p = figure(
                title="Box-select a region",
                tools="box_select,reset",
                active_drag="box_select",
            )
            p.scatter("x", "y", source=src, size=6, alpha=0.6)
            return p

    with ui.card(full_screen=True):

        @render_matplotlib
        def hist():
            indices = scatter.selected() or []
            fig, ax = plt.subplots()
            ax.hist(np.asarray(src.data["y"])[indices], bins=15)
            ax.set_title(f"y-distribution of the {len(indices)} selected points")
            return fig
