# Needs: pip install 'shinywidgets[leafmap,plotly]' pandas, or
# `uv run --with pandas,plotly shiny run 07_bounds_viewport_chart.py`.
import leafmap
import pandas as pd
import plotly.express as px
from shiny.express import ui
from shinywidgets import render_leafmap, render_plotly

CITIES = pd.read_csv(
    "https://raw.githubusercontent.com/opengeos/leafmap/master/examples/data/world_cities.csv"
)

ui.page_opts(title="Map viewport drives a chart", fillable=True)

with ui.layout_columns(col_widths=(7, 5)):

    @render_leafmap
    def map():
        m = leafmap.Map(center=(20, 0), zoom=2)
        m.add_points_from_xy(
            CITIES,
            x="longitude",
            y="latitude",
            layer_name="Cities",
            max_cluster_radius=40,
        )
        return m

    @render_plotly
    def top_cities():
        # map.bounds() is ((south, west), (north, east)); it cancels (renders
        # nothing) until the browser first reports a viewport
        (south, west), (north, east) = map.bounds()
        in_view = CITIES[
            CITIES.latitude.between(south, north) & CITIES.longitude.between(west, east)
        ].nlargest(10, "pop_max")
        return px.bar(
            in_view.sort_values("pop_max"),
            x="pop_max",
            y="name",
            orientation="h",
            title=f"Largest cities in view ({len(in_view)} shown)",
        )
