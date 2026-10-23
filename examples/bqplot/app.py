import bqplot
import numpy as np
import pandas as pd
from shiny import App, render, ui
from shinywidgets import output_widget, reactive_read, render_bqplot

rng = np.random.default_rng(1)

cars = pd.DataFrame(
    {
        "model": [f"Car {i + 1}" for i in range(150)],
        "weight": rng.uniform(1.5, 5.0, 150).round(2),
    }
)
cars["mpg"] = (45 - 6 * cars["weight"] + rng.normal(0, 2.5, 150)).round(1)

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.p(
            "Drag a box over the scatterplot to brush points. The brush updates the "
            "scatter's ",
            ui.tags.code("selected"),
            " trait, which Python reads reactively.",
        ),
        width=300,
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header("Brush to select cars"),
            output_widget("scatter"),
            full_screen=True,
        ),
        ui.card(
            ui.card_header("Selected cars"),
            ui.output_data_frame("selected_cars"),
        ),
        col_widths=[7, 5],
    ),
)


def server(input, output, session):
    @render_bqplot
    def scatter():
        x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
        points = bqplot.Scatter(
            x=cars["weight"].to_numpy(),
            y=cars["mpg"].to_numpy(),
            scales={"x": x_sc, "y": y_sc},
            colors=["steelblue"],
            unselected_style={"opacity": 0.3},
        )
        brush = bqplot.interacts.BrushSelector(
            x_scale=x_sc, y_scale=y_sc, marks=[points]
        )
        return bqplot.Figure(
            marks=[points],
            axes=[
                bqplot.Axis(scale=x_sc, label="Weight (1000 lbs)"),
                bqplot.Axis(scale=y_sc, orientation="vertical", label="MPG"),
            ],
            interaction=brush,
        )

    @render.data_frame
    def selected_cars():
        points = scatter.widget.marks[0]
        selected = reactive_read(points, "selected")
        if selected is None:
            return cars.iloc[0:0]
        return cars.iloc[list(selected)]


app = App(app_ui, server)
