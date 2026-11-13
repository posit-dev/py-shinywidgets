import ipyvolume as ipv
import numpy as np
import plotly.express as px
from shiny.express import render, ui

from shinywidgets import render_ipyvolume

# Table row selection -> 3D highlight: ipyvolume can't tell you which points a
# browser lasso covers (see Gotchas), but a table can drive a highlight the
# other way.
#
# This bakes the highlight into plain per-point `color`/`size` arrays rather
# than ipyvolume's dedicated `selected`/`size_selected`/`color_selected`
# mechanism. `selected` has two upstream bugs (see Gotchas): an empty
# `selected=[]` crashes the view, and -- verified separately -- even with a
# non-empty sentinel standing in for "nothing selected", the highlight only
# ever reflects the *first* value `selected` is set to after a figure
# renders; clicking a different row afterwards changes the trait (confirmed
# with `reactive_read`) but never moves the highlighted sphere, with no
# console error. Recomputing a plain color/size array on every selection
# sidesteps both bugs and re-renders the whole figure (the camera resets),
# which is a reasonable trade for a table-driven highlight.
ui.page_opts(title="Table row selection -> 3D highlight", fillable=True)

iris = px.data.iris()
palette = {1: (0.91, 0.30, 0.24), 2: (0.18, 0.49, 0.20), 3: (0.21, 0.45, 0.69)}
base_color = np.array([palette[i] for i in iris["species_id"]])
HIGHLIGHT = np.array([1.0, 1.0, 0.0])  # yellow

with ui.layout_columns():
    with ui.card():
        ui.card_header("Click a row to highlight it in 3D")

        @render.data_frame
        def table():
            return render.DataGrid(
                iris[["sepal_length", "petal_length", "sepal_width", "species"]],
                selection_mode="row",
                height="400px",
            )

    with ui.card():
        ui.card_header("Highlighted point")

        @render_ipyvolume
        def plot():
            rows = list(table.cell_selection()["rows"])
            color = base_color.copy()
            size = np.full(len(iris), 1.2)
            if rows:
                color[rows] = HIGHLIGHT
                size[rows] = 6
            fig = ipv.figure()
            ipv.scatter(
                iris["sepal_length"], iris["petal_length"], iris["sepal_width"],
                size=size, color=color, marker="sphere",
            )
            return fig
