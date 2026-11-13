# Click a point to show its full row in a detail card. hv.streams.Tap reports
# the data-space (x, y) of the click; the nearest row is looked up on the
# Shiny side, same recipe as the box-select example.
import holoviews as hv
import plotly.express as px
import hvplot.pandas  # noqa: F401
from shiny import reactive
from shiny.express import render, ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

tips = px.data.tips()
tap_xy = reactive.value(None)

ui.page_opts(title="Click a point for details", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):

        @render_holoviews
        def scatter():
            points = tips.hvplot.scatter(
                "total_bill", "tip", responsive=True, tools=["tap"]
            )
            hv.streams.Tap(source=points).add_subscriber(
                lambda x, y: tap_xy.set((x, y))
            )
            return points

    with ui.card():
        ui.card_header("Nearest table row")

        @render.ui
        def detail():
            xy = tap_xy()
            if xy is None:
                return ui.p("Click a point in the plot.", class_="text-muted")
            x, y = xy
            dist = (tips.total_bill - x) ** 2 + (tips.tip - y) ** 2
            row = tips.loc[dist.idxmin()]
            return ui.TagList(
                ui.h5(f"${row.total_bill:.2f} bill, ${row.tip:.2f} tip"),
                ui.p(f"{row['size']} people, {row.day} {row.time}, smoker: {row.smoker}"),
            )
