import matplotlib.dates as mdates
import pandas as pd
from plotnine import aes, geom_line, ggplot, labs, theme_minimal
from plotnine.data import economics
from shiny.express import render, ui
from shinywidgets import render_plotnine

ui.page_opts(title="Zoom drives a linked plot", fillable=True)


def visible_window():
    (x0, x1), _ = top.limits()
    lo = pd.Timestamp(mdates.num2date(x0).replace(tzinfo=None))
    hi = pd.Timestamp(mdates.num2date(x1).replace(tzinfo=None))
    return economics[(economics.date >= lo) & (economics.date <= hi)]


with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Unemployment -- zoom into a stretch")

        @render_plotnine
        def top():
            return (
                ggplot(economics, aes("date", "unemploy"))
                + geom_line()
                + labs(x="", y="Unemployed (thousands)")
                + theme_minimal()
            )

    with ui.card(full_screen=True):
        ui.card_header("Savings rate, same window")

        @render_plotnine
        def bottom():
            return (
                ggplot(visible_window(), aes("date", "psavert"))
                + geom_line(color="darkorange")
                + labs(x="", y="Personal savings rate (%)")
                + theme_minimal()
            )


with ui.card():
    ui.card_header("Summary of the visible window")

    @render.text
    def summary():
        visible = visible_window()
        return f"{len(visible)} months visible, average unemployment {visible.unemploy.mean():,.0f}k"
