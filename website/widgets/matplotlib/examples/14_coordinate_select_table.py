import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.widgets import RectangleSelector
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_matplotlib

ui.page_opts(fillable=True)

rng = np.random.default_rng(5)
cars = pd.DataFrame(
    {
        "model": [f"Car {i + 1}" for i in range(120)],
        "weight": rng.uniform(1.5, 5.0, 120).round(2),
    }
)
cars["mpg"] = (45 - 6 * cars["weight"] + rng.normal(0, 2.5, 120)).round(1)
selected = reactive.value(np.zeros(len(cars), dtype=bool))

with ui.layout_columns(col_widths=(7, 5)):

    @render_matplotlib
    def plot():
        fig = Figure(layout="constrained")
        ax = fig.subplots()
        points = ax.scatter(cars["weight"], cars["mpg"], alpha=0.7)
        ax.set_xlabel("Weight (1000 lbs)")
        ax.set_ylabel("Miles per gallon")

        def on_select(press, release):
            x0, x1 = sorted([press.xdata, release.xdata])
            y0, y1 = sorted([press.ydata, release.ydata])
            mask = cars["weight"].between(x0, x1) & cars["mpg"].between(y0, y1)
            points.set_facecolors(np.where(mask, "tab:orange", "tab:blue"))
            fig.canvas.draw_idle()
            selected.set(mask.to_numpy())

        fig._selector = RectangleSelector(ax, on_select, interactive=True)
        return fig

    with ui.card():

        @render.data_frame
        def table():
            return cars[selected()]
