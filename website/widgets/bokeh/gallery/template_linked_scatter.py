# Linked scatter + table (template)
#
# Two bokeh plots that share one ColumnDataSource, so a box or lasso selection
# in either plot highlights the same points in the other instantly (in the
# browser, no Python round trip needed for the link itself). The selection
# also flows to Python via `selected_rows()`, which drives a data table. Swap
# in your own columns and this scales to any 2-3 numeric-feature dataset.
#
# Run:
#     uv run --with bokeh_sampledata shiny run docs/widget-guides/bokeh/gallery/template_linked_scatter.py
#
# Data: bokeh's own sample-data package (`bokeh_sampledata`, downloaded on
# first use -- `pip install bokeh_sampledata`); Fisher's iris flowers.
# NOTE: this header is a `#` comment block, not a module docstring -- Shiny
# Express auto-displays a bare top-level string literal in the UI, so a
# triple-quoted docstring here would render as visible page text.

from bokeh.layouts import row
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.sampledata.iris import flowers
from bokeh.transform import factor_cmap
from shiny.express import render, ui
from shinywidgets import render_bokeh

ui.page_opts(title="Linked scatter", fillable=True)

src = ColumnDataSource(flowers)
species = sorted(flowers["species"].unique())
colors = factor_cmap("species", palette=["#1f77b4", "#ff7f0e", "#2ca02c"], factors=species)

with ui.card(full_screen=True, height="55%"):

    @render_bokeh
    def plots():
        tools = "box_select,lasso_select,reset"
        left = figure(
            title="sepal length vs. width",
            tools=tools,
            active_drag="box_select",
            sizing_mode="stretch_both",
        )
        left.scatter(
            "sepal_length", "sepal_width", source=src, size=8, alpha=0.7, color=colors
        )

        right = figure(
            title="petal length vs. width",
            tools=tools,
            active_drag="box_select",
            sizing_mode="stretch_both",
        )
        right.scatter(
            "petal_length", "petal_width", source=src, size=8, alpha=0.7, color=colors
        )

        return row(left, right, sizing_mode="stretch_both")


with ui.card(full_screen=True):
    ui.card_header("Selected rows")

    @render.data_frame
    def table():
        return plots.selected_rows()
