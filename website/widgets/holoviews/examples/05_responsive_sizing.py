# HoloViews and hvPlot plots are a fixed size (300x300, or 700x300 for
# hvPlot) by default, and get clipped by a smaller container. Pass
# `responsive=True` to make a plot fill its card instead.
import plotly.express as px
import hvplot.pandas  # noqa: F401
from shiny.express import ui

from shinywidgets import render_holoviews

tips = px.data.tips()

ui.page_opts(title="Fixed vs. responsive sizing", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Default: fixed size, clipped by the card")

        @render_holoviews
        def fixed():
            return tips.hvplot.hist("total_bill")

    with ui.card(full_screen=True):
        ui.card_header("responsive=True: fills the card")

        @render_holoviews
        def responsive():
            return tips.hvplot.hist("total_bill", responsive=True)
