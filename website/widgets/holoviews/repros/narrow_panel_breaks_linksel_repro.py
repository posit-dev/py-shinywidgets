import holoviews as hv
import plotly.express as px
import hvplot.pandas  # noqa: F401
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_holoviews

hv.extension("bokeh")
tips = px.data.tips()
ui.page_opts(title="narrow 3-panel, no sidebar", fillable=True)

links = hv.link_selections.instance(unselected_alpha=0.25)
sel = reactive.value(None)
_w = links.param.watch(lambda e: sel.set(e.new), "selection_expr")

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        @render_holoviews
        def charts():
            scatter = tips.hvplot.scatter("total_bill", "tip", responsive=True, title="Bill vs. tip")
            bill_hist = tips.hvplot.hist("total_bill", responsive=True, title="Bill distribution")
            size_hist = tips.hvplot.hist("size", responsive=True, title="Party size")
            return links(scatter + bill_hist + size_hist).opts(shared_axes=False)
    with ui.card():
        ui.markdown("placeholder")

@reactive.calc
def n_selected():
    expr = sel()
    if expr is None:
        return len(tips)
    return len(links.filter(tips, selection_expr=expr))

@render.text
def readout():
    return f"selected: {n_selected()} of {len(tips)}"
