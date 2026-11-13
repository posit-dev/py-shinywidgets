# link_selections crossfilters the plots on its own, but its selection is
# also a param event -- watch it to bring the same selection into ordinary
# Shiny outputs (here, two value boxes).
import holoviews as hv
import plotly.express as px
import hvplot.pandas  # noqa: F401
from shiny import reactive
from shiny.express import render, ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

tips = px.data.tips()

ui.page_opts(title="Crossfilter dashboard", fillable=True)

links = hv.link_selections.instance()
selection_expr = reactive.value(None)
_watcher = links.param.watch(
    lambda event: selection_expr.set(event.new), "selection_expr"
)


@reactive.calc
def selected():
    expr = selection_expr()
    return tips if expr is None else links.filter(tips, selection_expr=expr)


with ui.layout_columns(fill=False):
    with ui.value_box():
        "Rows selected"

        @render.text
        def n_selected():
            return f"{len(selected())} of {len(tips)}"

    with ui.value_box():
        "Average tip %"

        @render.text
        def avg_pct():
            sel = selected()
            if not len(sel):
                return "-"
            return f"{(sel.tip / sel.total_bill).mean():.1%}"

with ui.card(full_screen=True):

    @render_holoviews
    def crossfilter():
        scatter = tips.hvplot.scatter(
            "total_bill", "tip", responsive=True, title="Bill vs. tip"
        ).opts(active_tools=["box_select"])
        tip_hist = tips.hvplot.hist(
            "tip", responsive=True, title="Tip distribution"
        ).opts(active_tools=["box_select"])
        return links(scatter + tip_hist).opts(shared_axes=False)
