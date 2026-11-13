from plotnine import aes, facet_wrap, geom_point, ggplot, labs, theme_minimal
from plotnine.data import mpg
from shiny.express import render, ui
from shinywidgets import render_plotnine

ui.page_opts(title="plot.limits(ax): which facet panel?", fillable=True)

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
        ui.card_header("Per-panel x ranges")

        @render.code
        def ranges():
            n = len(plot.widget.figure.axes)
            lines = []
            for i in range(n):
                x0, x1 = plot.limits(ax=i)[0]
                lines.append(f"ax={i}: {x0:.2f} to {x1:.2f}")
            return "\n".join(lines)
