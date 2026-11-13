# hv.link_selections crossfilters every plot it wraps: box-select in one chart
# and the others (plus any held-out, non-selected points) restyle to match --
# no Python callback written. A composite Layout like this defaults its drag
# tool to Pan, not Box Select, regardless of panel width -- set
# active_tools=["box_select"] on each element so box-select is the
# ready-to-use default instead.
import holoviews as hv
import plotly.express as px
import hvplot.pandas  # noqa: F401
from shiny.express import ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

tips = px.data.tips()

ui.page_opts(title="Crossfilter with link_selections", fillable=True)

# One instance per session (Express re-runs this module per session). A
# module-level instance would show every visitor's selection to everyone else.
links = hv.link_selections.instance(unselected_alpha=0.3)


@render_holoviews
def crossfilter():
    scatter = tips.hvplot.scatter(
        "total_bill", "tip", responsive=True, title="Bill vs. tip"
    ).opts(active_tools=["box_select"])
    bill_hist = tips.hvplot.hist(
        "total_bill", responsive=True, title="Bill distribution"
    ).opts(active_tools=["box_select"])
    size_hist = tips.hvplot.hist("size", responsive=True, title="Party size").opts(
        active_tools=["box_select"]
    )
    # Drag directly on any plot below to crossfilter the others -- box-select
    # is already the active drag tool on every panel, no toolbar click needed.
    return links(scatter + bill_hist + size_hist).opts(shared_axes=False)
