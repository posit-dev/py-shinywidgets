from __future__ import annotations

import altair as alt
import ipyleaflet as L
import plotly.express as px
from bokeh.plotting import figure
from itables.widget import ITable
from maplibre import Map as MaplibreMap
from maplibre import MapOptions
from maplibre.basemaps import Carto
from matplotlib.figure import Figure
from reactable import Reactable
from shiny.express import ui
from shinywidgets import (
    render_altair,
    render_bokeh,
    render_ipyleaflet,
    render_itables,
    render_maplibre,
    render_matplotlib,
    render_plotly,
    render_reactable,
)

cars = px.data.tips()

ui.page_opts(title="Dark mode: who follows, who doesn't", fillable=True)
ui.input_dark_mode(id="mode")

# lonboard is covered separately, in 04_dark_mode_lonboard.py: on the same
# page as maplibre it fails to render at all (see NOTES.md -- the two
# widgets' bundled copies of deck.gl collide: "deck.gl - multiple versions
# detected"), unrelated to dark mode.
with ui.layout_columns(col_widths=[4, 4, 4]):
    with ui.card():
        ui.card_header("plotly")

        @render_plotly
        def plot_plotly():
            return px.scatter(cars, x="total_bill", y="tip", color="sex")

    with ui.card():
        ui.card_header("altair")

        @render_altair
        def plot_altair():
            return (
                alt.Chart(cars)
                .mark_circle()
                .encode(x="total_bill:Q", y="tip:Q", color="sex:N")
            )

    with ui.card():
        ui.card_header("bokeh")

        @render_bokeh
        def plot_bokeh():
            p = figure(sizing_mode="stretch_both")
            p.scatter(cars["total_bill"], cars["tip"])
            return p

    with ui.card():
        ui.card_header("matplotlib")

        @render_matplotlib
        def plot_matplotlib():
            fig = Figure(layout="constrained")
            ax = fig.subplots()
            ax.scatter(cars["total_bill"], cars["tip"])
            return fig

    with ui.card():
        ui.card_header("itables")

        @render_itables
        def tbl_itables():
            return ITable(cars.head(20))

    with ui.card():
        ui.card_header("reactable")

        @render_reactable
        def tbl_reactable():
            return Reactable(cars.head(20))

    with ui.card():
        ui.card_header("ipyleaflet")

        @render_ipyleaflet
        def map_ipyleaflet():
            return L.Map(center=(39.8, -98.5), zoom=3)

    with ui.card():
        ui.card_header("maplibre")

        @render_maplibre
        def map_maplibre():
            return MaplibreMap(
                MapOptions(style=Carto.POSITRON, center=(-98.5, 39.8), zoom=2.5)
            )
