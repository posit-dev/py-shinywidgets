# Compose plots with `*` (overlay, same axes) and `+` (layout, side by side) --
# no subplot bookkeeping required.
import holoviews as hv
import plotly.express as px
import hvplot.pandas  # noqa: F401
from shiny.express import ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

tips = px.data.tips()
by_day = tips.groupby("day", observed=True)["tip"].mean().reindex(
    ["Thur", "Fri", "Sat", "Sun"]
)

ui.page_opts(title="Overlay and layout", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Overlay (*): scatter + a reference line, shared axes")

        @render_holoviews
        def overlay():
            points = tips.hvplot.scatter(
                "total_bill", "tip", responsive=True, color="gray", alpha=0.5
            )
            rule = hv.Slope(0.15, 0).opts(color="firebrick", line_width=2)
            return (points * rule).opts(title="15% tip reference line")

    with ui.card(full_screen=True):
        ui.card_header("Layout (+): two independent plots, one call")

        @render_holoviews
        def layout():
            bars = by_day.hvplot.bar(
                responsive=True, title="Average tip by day", ylabel="tip"
            )
            hist = tips.hvplot.hist(
                "total_bill", responsive=True, title="Bill distribution"
            )
            return (bars + hist).opts(shared_axes=False)
