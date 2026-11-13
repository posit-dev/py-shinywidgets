# Periodic table explorer (showcase)
#
# The periodic table grid linked to a property scatter (electronegativity vs.
# atomic radius), sharing one ColumnDataSource and colored by each element's
# real CPK color, with a dark theme. Box-select elements in either plot and
# the same elements light up in the other instantly (browser-only link);
# `selected_rows()` feeds a live Python summary and a details table. A
# slider rescales marker size by atomic mass in place (no re-render, so
# selection and zoom survive) via a single-column `source.data["size"] =`
# assignment.
#
# Run:
#     uv run --with bokeh_sampledata shiny run docs/widget-guides/bokeh/gallery/showcase_star_explorer.py
#
# Data: bokeh's own sample-data package (`bokeh_sampledata`, downloaded on
# first use -- `pip install bokeh_sampledata`). Noble gases (no recorded
# electronegativity) and the lanthanides/actinides (no single periodic-table
# group) are left out for a cleaner grid.

import numpy as np
from bokeh.document import Document
from bokeh.layouts import row
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.sampledata.periodic_table import elements
from bokeh.themes import built_in_themes
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_bokeh

ui.page_opts(title="Periodic table explorer", fillable=True)

df = elements[elements["group"] != "-"].dropna(
    subset=["atomic radius", "electronegativity"]
)
df = df.assign(group=df["group"].astype(int), size=6.0)
n = len(df)
src = ColumnDataSource(df)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True, height="65%"):

        @render_bokeh
        def plots():
            doc = Document(theme=built_in_themes["night_sky"])
            tools = "box_select,reset"

            grid = figure(
                title="Periodic table (by group and period)",
                x_range=(0, 19),
                y_range=(8, 0),
                tools=tools,
                active_drag="box_select",
                sizing_mode="stretch_both",
            )
            grid.xaxis.axis_label = "group"
            grid.yaxis.axis_label = "period"
            grid.scatter(
                "group", "period", source=src, size="size", color="CPK",
                line_color="gray",
            )

            props = figure(
                title="Electronegativity vs. atomic radius",
                tools=tools,
                active_drag="box_select",
                sizing_mode="stretch_both",
            )
            props.xaxis.axis_label = "atomic radius (pm)"
            props.yaxis.axis_label = "electronegativity"
            props.scatter(
                "atomic radius", "electronegativity", source=src, size="size",
                color="CPK", line_color="gray",
            )

            layout = row(grid, props, sizing_mode="stretch_both")
            doc.add_root(layout)
            return layout

    with ui.card(full_screen=True):
        ui.card_header("Selection")
        ui.input_slider("size", "Marker size", min=4, max=20, value=6, step=1)

        @render.text
        def summary():
            rows = plots.selected_rows()
            if len(rows) == 0:
                return "Box-select elements in either plot."
            return (
                f"{len(rows)} elements selected\n"
                f"mean atomic radius: {rows['atomic radius'].mean():.0f} pm\n"
                f"mean electronegativity: {rows['electronegativity'].mean():.2f}"
            )

        @render.data_frame
        def table():
            rows = plots.selected_rows()[["symbol", "name", "metal"]]
            return render.DataGrid(rows, height="300px")


@reactive.effect
def _():
    # In-place restyle: the slider updates one column without touching the
    # rest of the data or resetting the plots' zoom/selection.
    src.data["size"] = np.full(n, float(input.size()))
