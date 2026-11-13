import numpy as np
from matplotlib.figure import Figure
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_matplotlib

ui.page_opts(fillable=True)
ui.input_action_button("save", "Save current view")

t = np.linspace(0, 50, 4000)
y = np.sin(t) + 0.3 * np.sin(5 * t) + 0.02 * t**1.2
bookmarks = reactive.value([])


@render_matplotlib
def plot():
    fig = Figure(layout="constrained")
    ax = fig.subplots()
    ax.plot(t, y, lw=0.8)
    return fig


@reactive.effect
@reactive.event(input.save)
def _save_view():
    (x0, x1), _ = plot.limits()
    bookmarks.set([*bookmarks(), f"{x0:.1f} to {x1:.1f}"])


@render.code
def saved():
    views = bookmarks()
    if not views:
        return "No views saved yet -- zoom in, then click Save."
    return "\n".join(f"{i + 1}. {v}" for i, v in enumerate(views))
