# Tips explorer: crossfilter three linked charts, click a point in a separate
# plot for its details, and filter by day -- all driven by HoloViews streams
# and link_selections, with no Bokeh server and no Python callback for the
# linking itself.
# Bucket: showcase.
# Run:  uv run shiny run docs/widget-guides/holoviews/gallery/showcase_tips_explorer.py
# Data: plotly.express.data.tips() (ships with plotly)
import holoviews as hv
import plotly.express as px
import hvplot.pandas  # noqa: F401
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

tips = px.data.tips()
ALL_DAYS = ["Thur", "Fri", "Sat", "Sun"]

ui.page_opts(title="Tips explorer", fillable=True)

with ui.sidebar(width=240):
    ui.input_checkbox_group("days", "Day", ALL_DAYS, selected=ALL_DAYS)
    ui.markdown(
        "Drag a box-select on any chart to crossfilter the others. Click a "
        "point in the smaller plot for its details."
    )

# One link_selections instance (and one tap reactive.Value) per session
# (Express re-runs this file per session, so top-level code here is already
# per-session).
links = hv.link_selections.instance(unselected_alpha=0.25)
selection_expr = reactive.value(None)
tap_xy = reactive.value(None)
_watcher = links.param.watch(
    lambda event: selection_expr.set(event.new), "selection_expr"
)


@reactive.calc
def day_filtered():
    return tips[tips.day.isin(input.days())]


@reactive.calc
def crossfiltered():
    df = day_filtered()
    expr = selection_expr()
    return df if expr is None else links.filter(df, selection_expr=expr)


with ui.layout_columns(fill=False):
    with ui.value_box():
        "Rows selected"

        @render.text
        def n_selected():
            return f"{len(crossfiltered())} of {len(day_filtered())}"

    with ui.value_box():
        "Average tip %"

        @render.text
        def avg_pct():
            sel = crossfiltered()
            if not len(sel):
                return "-"
            return f"{(sel.tip / sel.total_bill).mean():.1%}"

    with ui.value_box():
        "Busiest meal"

        @render.text
        def busiest_meal():
            sel = crossfiltered()
            if not len(sel):
                return "-"
            return sel.time.value_counts().idxmax()

with ui.card(full_screen=True):
    ui.card_header("Crossfiltered charts")

    # Full row width is a layout preference here, not a bug workaround (an
    # earlier draft wrongly blamed a width threshold for a box-select failure
    # that was actually a missing active_tools setting -- see NOTES.md).
    # active_tools=["box_select"] on each element below is what actually
    # matters: without it, a link_selections-wrapped composite Layout
    # defaults its drag tool to Pan, at any width.
    @render_holoviews
    def charts():
        df = day_filtered()
        scatter = df.hvplot.scatter(
            "total_bill", "tip", responsive=True, title="Bill vs. tip"
        ).opts(active_tools=["box_select"])
        bill_hist = df.hvplot.hist(
            "total_bill", responsive=True, title="Bill distribution"
        ).opts(active_tools=["box_select"])
        size_hist = df.hvplot.hist("size", responsive=True, title="Party size").opts(
            active_tools=["box_select"]
        )
        return links(scatter + bill_hist + size_hist).opts(shared_axes=False)

with ui.layout_columns(col_widths=[4, 8]):
    with ui.card(full_screen=True):
        ui.card_header("Click a point for details")

        # A separate, unlinked, fixed-size plot: a Tap stream on an element
        # that's also wrapped by link_selections never fires (see the
        # guide's gotchas).
        @render_holoviews
        def click_plot():
            df = day_filtered()
            points = df.hvplot.scatter(
                "total_bill", "tip", width=320, height=220, tools=["tap"]
            )
            hv.streams.Tap(source=points).add_subscriber(
                lambda x, y: tap_xy.set((x, y))
            )
            return points

        @render.ui
        def detail():
            xy = tap_xy()
            if xy is None:
                return ui.p("Click a point in the plot above.", class_="text-muted")
            x, y = xy
            df = day_filtered()
            dist = (df.total_bill - x) ** 2 + (df.tip - y) ** 2
            row = df.loc[dist.idxmin()]
            pct = row.tip / row.total_bill
            return ui.TagList(
                ui.h5(f"${row.total_bill:.2f} bill, ${row.tip:.2f} tip ({pct:.0%})"),
                ui.p(f"{row['size']} people, {row.day} {row.time}"),
            )

    with ui.card(full_screen=True):
        ui.card_header("Crossfiltered rows")

        @render.data_frame
        def table():
            return render.DataGrid(crossfiltered(), height="350px")
