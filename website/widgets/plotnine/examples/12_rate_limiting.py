from plotnine import aes, geom_line, ggplot, labs, theme_minimal
from plotnine.data import economics
from shiny.express import render, ui
from shinywidgets import render_plotnine

ui.page_opts(fillable=True)

counts = {"default": 0, "fast": 0}


def make_plot():
    return (
        ggplot(economics, aes("date", "unemploy"))
        + geom_line()
        + labs(x="", y="Unemployed (thousands)")
        + theme_minimal()
    )


with ui.layout_columns():
    with ui.card():
        ui.card_header("default: debounced 250ms")

        @render_plotnine
        def default_out():
            return make_plot()

        @render.code
        def default_count():
            default_out.limits()
            counts["default"] += 1
            return f"limits() recomputed {counts['default']} times"

    with ui.card():
        ui.card_header("rate_delay=0: every event")

        @render_plotnine(rate_delay=0)
        def fast_out():
            return make_plot()

        @render.code
        def fast_count():
            fast_out.limits()
            counts["fast"] += 1
            return f"limits() recomputed {counts['fast']} times"
