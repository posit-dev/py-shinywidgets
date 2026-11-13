import holoviews as hv
import plotly.express as px
import hvplot.pandas  # noqa: F401
from shiny.express import ui
from shinywidgets import render_holoviews

hv.extension("bokeh")
df = px.data.tips()
ui.page_opts(title="sidebar test", fillable=True)

with ui.sidebar(width=240):
    ui.markdown("just a sidebar")

links = hv.link_selections.instance(unselected_alpha=0.3)

with ui.card(full_screen=True):
    @render_holoviews
    def charts():
        scatter = df.hvplot.scatter("total_bill", "tip", responsive=True, title="Bill vs. tip")
        hist = df.hvplot.hist("total_bill", responsive=True, title="Bill distribution")
        return links(scatter + hist).opts(shared_axes=False)
