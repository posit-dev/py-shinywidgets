import numpy as np
from plotnine import aes, facet_wrap, geom_point, ggplot, labs, theme_minimal
from plotnine.data import mpg
from shiny import reactive, req
from shiny.express import render, ui
from shinywidgets import render_plotnine

ui.page_opts(title="Click a facet, know the panel", fillable=True)
found = reactive.value(None)

with ui.layout_columns():
    with ui.card(full_screen=True):

        @render_plotnine
        def plot():
            return (
                ggplot(mpg, aes("displ", "hwy"))
                + geom_point(size=2, alpha=0.7)
                + facet_wrap("~drv", labeller="label_both")
                + labs(x="Displacement (L)", y="Highway MPG")
                + theme_minimal()
            )

    with ui.card():
        ui.card_header("Clicked panel")

        @render.ui
        def detail():
            drv, row = req(found())
            return ui.p(
                f"drv = {drv}: {row.manufacturer.title()} {row.model} "
                f"({row.displ} L, {row.hwy} MPG)"
            )


@reactive.effect
def _locate_click():
    event = plot.clicked()
    canvas = plot.widget
    req(event, canvas)
    # Facets are separate matplotlib axes; plotnine's own layout table (built
    # while drawing) says which facet value each one holds, in `figure.axes`
    # order.
    panel = canvas.figure.get_layout_engine().plot.facet.layout.layout
    i = canvas.figure.axes.index(event.inaxes)
    drv = panel["drv"].iloc[i]

    subset = mpg[mpg["drv"] == drv].reset_index(drop=True)
    xy = event.inaxes.transData.transform(subset[["displ", "hwy"]].to_numpy())
    j = int(np.hypot(xy[:, 0] - event.x, xy[:, 1] - event.y).argmin())
    found.set((drv, subset.iloc[j]))
