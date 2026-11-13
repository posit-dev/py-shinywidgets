# Crossfilter template: two hvPlot charts linked with hv.link_selections.
# Bucket: template. Drag a box-select on either chart to filter both -- zero
# Python callbacks for the linking itself. active_tools=["box_select"] on
# each element makes box-select the default drag tool (a composite Layout
# otherwise defaults to Pan).
# Run:  uv run shiny run docs/widget-guides/holoviews/gallery/template_crossfilter.py
# Data: plotly.express.data.tips() (ships with plotly)
import holoviews as hv
import plotly.express as px
import hvplot.pandas  # noqa: F401
from shiny.express import ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

df = px.data.tips()

ui.page_opts(title="Crossfilter template", fillable=True)

# One link_selections instance per session: Express re-runs this file per
# session, so a plain module-level assignment here is already per-session.
links = hv.link_selections.instance(unselected_alpha=0.3)

with ui.card(full_screen=True):
    ui.card_header("Drag a box-select on either chart")

    @render_holoviews
    def charts():
        scatter = df.hvplot.scatter(
            "total_bill", "tip", responsive=True, title="Bill vs. tip"
        ).opts(active_tools=["box_select"])
        hist = df.hvplot.hist(
            "total_bill", responsive=True, title="Bill distribution"
        ).opts(active_tools=["box_select"])
        return links(scatter + hist).opts(shared_axes=False)
