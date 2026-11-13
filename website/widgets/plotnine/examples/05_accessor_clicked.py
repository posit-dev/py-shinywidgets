import numpy as np
from plotnine import aes, geom_point, ggplot, labs, theme_minimal
from plotnine.data import mpg
from shiny import reactive, req
from shiny.express import render, ui
from shinywidgets import render_plotnine

ui.page_opts(title="plot.clicked(): nearest point", fillable=True)
nearest = reactive.value(None)

with ui.layout_columns():
    with ui.card(full_screen=True):

        @render_plotnine
        def plot():
            return (
                ggplot(mpg, aes("displ", "hwy"))
                + geom_point(size=2.5, alpha=0.7)
                + labs(x="Displacement (L)", y="Highway MPG")
                + theme_minimal()
            )

    with ui.card():
        ui.card_header("Clicked car")

        @render.ui
        def detail():
            # Compare to None explicitly: a row position of 0 is falsy, so
            # req(nearest()) would wrongly treat that valid click as "no click"
            i = nearest()
            if i is None:
                return ui.p("Click a point to see that car here.")
            row = mpg.iloc[i]
            return ui.p(
                f"{row.manufacturer.title()} {row.model}: {row.displ} L, {row.hwy} MPG hwy"
            )


@reactive.effect
def _mark_nearest():
    event = plot.clicked()
    canvas = plot.widget
    req(event, canvas)
    ax = canvas.figure.axes[0]
    xy = ax.transData.transform(mpg[["displ", "hwy"]].to_numpy())
    i = int(np.hypot(xy[:, 0] - event.x, xy[:, 1] - event.y).argmin())
    nearest.set(i)

    for artist in list(ax.lines):
        if artist.get_label() == "_clicked":
            artist.remove()
    row = mpg.iloc[i]
    ax.plot(
        [row.displ],
        [row.hwy],
        "o",
        ms=14,
        mfc="none",
        mec="black",
        mew=2,
        label="_clicked",
    )
    canvas.draw_idle()
