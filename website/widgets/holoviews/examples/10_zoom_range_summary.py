# hv.streams.RangeXY reports the plot's current pan/zoom range -- store the
# range itself (not a counter) in the reactive.Value. RangeXY fires once on
# mount with the default range and again on every zoom/pan, including
# transiently during a drag; storing an ever-changing value like a counter
# caused a runaway re-render loop on older shinywidgets versions (fixed --
# see the guide's gotchas section) and is still wasted invalidation. Storing
# the actual range is idempotent: reactive.Value.set() skips invalidation
# when the new value equals the old one, so repeats of the same range are a
# no-op and only a genuine zoom/pan triggers a recompute.
import holoviews as hv
import plotly.express as px
import hvplot.pandas  # noqa: F401
from shiny import reactive
from shiny.express import render, ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

tips = px.data.tips()

ui.page_opts(title="Zoom range -> visible-point summary", fillable=True)

range_val = reactive.value((None, None))


@render_holoviews
def scatter():
    points = tips.hvplot.scatter("total_bill", "tip", responsive=True)
    hv.streams.RangeXY(source=points).add_subscriber(
        lambda x_range, y_range: range_val.set((x_range, y_range))
    )
    return points


@reactive.calc
def visible():
    x_range, y_range = range_val()
    sub = tips
    if x_range is not None:
        sub = sub[sub.total_bill.between(*x_range)]
    if y_range is not None:
        sub = sub[sub.tip.between(*y_range)]
    return sub


@render.text
def summary():
    x_range, _ = range_val()
    if x_range is None:
        return f"{len(visible())} of {len(tips)} points visible (full range)"
    lo, hi = x_range
    return f"{len(visible())} of {len(tips)} points visible (total_bill {lo:.0f}-{hi:.0f})"
