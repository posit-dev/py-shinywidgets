import shiny as sh
import plotly.graph_objects as go
import ipywidgets as widgets
import pandas as pd
import numpy as np
from ipyshiny import output_widget, render_widget

cars_df = pd.read_csv(
    "https://raw.githubusercontent.com/plotly/datasets/master/imports-85.csv"
)

# Build parcats dimensions
categorical_dimensions = ["drive-wheels", "body-style", "fuel-type"]

dimensions = [
    dict(values=cars_df[label], label=label) for label in categorical_dimensions
]

# Build colorscale
color = np.zeros(len(cars_df), dtype="uint8")
colorscale = [
    [0, "gray"],
    [0.33, "gray"],
    [0.33, "firebrick"],
    [0.66, "firebrick"],
    [0.66, "blue"],
    [1.0, "blue"],
]
cmin = -0.5
cmax = 2.5

app_ui = sh.ui.page_fluid("Can has plotly FigureWidget", output_widget("fig"))


def server(input: sh.Inputs, output: sh.Outputs, session: sh.Session):

    fig = go.FigureWidget(
        data=[
            go.Scatter(
                x=cars_df.horsepower,
                y=cars_df["highway-mpg"],
                marker={
                    "color": color,
                    "cmin": cmin,
                    "cmax": cmax,
                    "colorscale": colorscale,
                    "showscale": False,
                },
                mode="markers",
                text=cars_df["make"],
            ),
            go.Parcats(
                domain={"x": [0, 0.45]},
                dimensions=dimensions,
                line={
                    "colorscale": colorscale,
                    "cmin": cmin,
                    "cmax": cmax,
                    "color": color,
                    "shape": "hspline",
                },
            ),
        ]
    ).update_layout(
        height=600,
        xaxis={"title": "Horsepower", "domain": [0.55, 1]},
        yaxis={"title": "MPG"},
        dragmode="lasso",
        hovermode="closest",
    )

    color_toggle = widgets.ToggleButtons(
        options=["None", "Red", "Blue"],
        index=1,
        description="Brush Color:",
        disabled=False,
    )

    def update_color(trace, points, state):
        new_color = np.array(fig.data[0].marker.color)
        new_color[points.point_inds] = color_toggle.index

        with fig.batch_update():
            fig.data[0].marker.color = new_color
            fig.data[1].line.color = new_color

    fig.data[0].on_selection(update_color)
    fig.data[1].on_click(update_color)

    @output(name="fig")
    @render_widget()
    def _():
        return widgets.VBox([color_toggle, fig])


app = sh.App(app_ui, server)
