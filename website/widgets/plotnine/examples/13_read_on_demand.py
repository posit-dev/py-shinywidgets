from plotnine import aes, geom_point, ggplot, labs, theme_minimal
from plotnine.data import mpg
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_plotnine

ui.page_opts(title="Save the current zoom window", fillable=True)
ui.input_action_button("save", "Save current view")

bookmarks = reactive.value([])


@render_plotnine
def plot():
    return (
        ggplot(mpg, aes("displ", "hwy", color="class"))
        + geom_point(size=2.5, alpha=0.8)
        + labs(x="Displacement (L)", y="Highway MPG", color="Class")
        + theme_minimal()
    )


@reactive.effect
@reactive.event(input.save)
def _save_view():
    (x0, x1), (y0, y1) = plot.limits()
    bookmarks.set([*bookmarks(), f"x: {x0:.1f}-{x1:.1f}, y: {y0:.1f}-{y1:.1f}"])


@render.code
def saved():
    views = bookmarks()
    if not views:
        return "No views saved yet -- zoom in, then click Save."
    return "\n".join(f"{i + 1}. {v}" for i, v in enumerate(views))
