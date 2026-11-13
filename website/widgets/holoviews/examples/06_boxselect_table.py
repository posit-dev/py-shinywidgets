# The recipe for reacting to a HoloViews stream in Shiny: subscribe to it, and
# set a `reactive.Value` from the callback. The stream runs outside Shiny's
# render cycle, but setting a reactive value from it still invalidates
# whatever reads that value, same as any other reactive.Value.
import holoviews as hv
import plotly.express as px
import hvplot.pandas  # noqa: F401
from shiny import reactive
from shiny.express import render, ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

tips = px.data.tips()

ui.page_opts(title="Box-select to filter a table", fillable=True)

bounds_val = reactive.value(None)


@render_holoviews
def scatter():
    points = tips.hvplot.scatter(
        "total_bill", "tip", responsive=True, tools=["box_select"]
    ).opts(active_tools=["box_select"])
    hv.streams.BoundsXY(source=points).add_subscriber(
        lambda bounds: bounds_val.set(bounds)
    )
    return points


@render.data_frame
def selected_rows():
    b = bounds_val()
    if b is None:
        return tips.iloc[:0]  # empty frame until the first selection
    x0, y0, x1, y1 = b
    sel = tips[tips.total_bill.between(x0, x1) & tips.tip.between(y0, y1)]
    return render.DataGrid(sel, height="250px")
