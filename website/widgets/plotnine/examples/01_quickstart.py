from plotnine import aes, geom_point, geom_smooth, ggplot, labs, theme_minimal
from plotnine.data import mpg
from shiny.express import ui
from shinywidgets import render_plotnine

ui.page_opts(title="plotnine quick start", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Engine displacement vs. highway MPG")

    @render_plotnine
    def plot():
        return (
            ggplot(mpg, aes("displ", "hwy", color="class"))
            + geom_point(size=2.5, alpha=0.8)
            + geom_smooth(method="lm", color="black", se=False)
            + labs(x="Displacement (L)", y="Highway MPG", color="Class")
            + theme_minimal()
        )
