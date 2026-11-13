import matplotlib.dates as mdates
from plotnine import aes, geom_line, ggplot, labs, theme_minimal
from plotnine.data import economics
from shiny.express import render, ui
from shinywidgets import render_plotnine

ui.page_opts(title="plot.limits(): zoom is a query", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):

        @render_plotnine
        def plot():
            return (
                ggplot(economics, aes("date", "unemploy"))
                + geom_line()
                + labs(x="", y="Unemployed (thousands)")
                + theme_minimal()
            )

    with ui.card():
        ui.card_header("Visible window")

        @render.text
        def window():
            (x0, x1), _ = plot.limits()
            # x0/x1 are plotnine's *transformed* x values -- here matplotlib's
            # date-number epoch, not a datetime -- convert to read them
            lo, hi = mdates.num2date(x0), mdates.num2date(x1)
            return f"{lo:%b %Y} to {hi:%b %Y}"
