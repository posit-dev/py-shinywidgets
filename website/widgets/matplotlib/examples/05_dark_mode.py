import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from shiny.express import input, ui
from shinywidgets import render_matplotlib

ui.page_opts(fillable=True)
ui.input_dark_mode(id="mode")

t = np.linspace(0, 2 * np.pi, 200)


@render_matplotlib
def plot():
    style = "dark_background" if input.mode() == "dark" else "default"
    with plt.style.context(style):
        fig = Figure(layout="constrained")
        ax = fig.subplots()
        ax.plot(t, np.sin(t))
        ax.plot(t, np.cos(t))
    # Transparent background so the card's own color shows through instead of
    # matplotlib's opaque white/black
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)
    return fig
