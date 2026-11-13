from plotnine import aes, geom_line, ggplot, labs, theme_minimal
from plotnine.data import economics
from shiny.express import ui
from shinywidgets import render_plotnine

ui.page_opts(title="Zoom and pan, no extra code", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("US unemployment, 1967-2015 -- hover to reveal the toolbar")

    @render_plotnine
    def plot():
        return (
            ggplot(economics, aes("date", "unemploy"))
            + geom_line()
            + labs(x="", y="Unemployed (thousands)")
            + theme_minimal()
        )
