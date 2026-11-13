from plotnine import aes, facet_wrap, geom_point, ggplot, labs, theme_light
from plotnine.data import mpg
from shiny.express import ui
from shinywidgets import render_plotnine

ui.page_opts(title="Facets that relayout live", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Highway MPG by displacement, faceted by drivetrain")

    @render_plotnine
    def plot():
        return (
            ggplot(mpg, aes("displ", "hwy", color="class"))
            + geom_point(size=2)
            + facet_wrap("~drv", labeller="label_both")
            + labs(x="Displacement (L)", y="Highway MPG", color="Class")
            + theme_light()
        )
