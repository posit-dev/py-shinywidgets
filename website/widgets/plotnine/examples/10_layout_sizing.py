from plotnine import aes, geom_point, ggplot, theme, theme_minimal
from plotnine.data import mpg
from shiny.express import ui
from shinywidgets import render_plotnine

ui.page_opts(fillable=True)


def scatter():
    return ggplot(mpg, aes("displ", "hwy")) + geom_point() + theme_minimal()


with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Fills its card (default)")

        @render_plotnine
        def fills():
            return scatter()

    with ui.card():
        ui.card_header("Explicit height: set a matching figure_size")

        @render_plotnine(height="220px")
        def fixed():
            return scatter() + theme(figure_size=(4, 2.2))
