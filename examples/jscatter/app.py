import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_jscatter

rng = np.random.default_rng(1)

n = 5000
origin = pd.Series(rng.choice(["USA", "Europe", "Japan"], n, p=[0.5, 0.25, 0.25]))
weight = origin.map({"USA": 3.4, "Europe": 2.6, "Japan": 2.4}) + rng.normal(0, 0.5, n)
cars = pd.DataFrame(
    {
        "origin": origin.astype("category"),
        "weight": weight.round(2),
        "mpg": (45 - 6 * weight + rng.normal(0, 2.5, n)).round(1),
        "hp": (45 * weight + rng.normal(0, 25, n)).round(),
    }
)

app_ui = ui.page_fillable(
    ui.p(
        "Drag with the lasso tool (or press and hold, then drag) on either plot to "
        "select points. The selection shows up in the other plot and in the table, "
        "all through reactive values on the Python side.",
        class_="text-muted small mb-0",
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header("Weight vs. MPG"),
            output_widget("weight_mpg"),
            full_screen=True,
        ),
        ui.card(
            ui.card_header("Horsepower vs. MPG"),
            output_widget("hp_mpg"),
            full_screen=True,
        ),
        ui.card(
            ui.card_header(ui.output_text("n_selected")),
            ui.output_data_frame("selected_cars"),
            full_screen=True,
        ),
        col_widths=[4, 4, 4],
    ),
)


def server(input, output, session):
    @render_jscatter
    def weight_mpg():
        return (
            Scatter(data=cars, x="weight", y="mpg", color_by="origin")
            .axes(labels=["Weight (1000 lbs)", "MPG"])
            .lasso(initiator=True)
        )

    @render_jscatter
    def hp_mpg():
        return (
            Scatter(data=cars, x="hp", y="mpg", color_by="origin")
            .axes(labels=["Horsepower", "MPG"])
            .lasso(initiator=True)
        )

    # Linked brushing: mirror each plot's selection onto the other one
    def link(source, target):
        @reactive.effect
        def _():
            selection = reactive_read(source.widget, "selection")
            with reactive.isolate():
                if not np.array_equal(selection, target.widget.selection):
                    target.widget.selection = selection

    link(weight_mpg, hp_mpg)
    link(hp_mpg, weight_mpg)

    @reactive.calc
    def selection():
        return reactive_read(weight_mpg.widget, "selection")

    @render.text
    def n_selected():
        return f"{len(selection()):,} of {len(cars):,} cars selected"

    @render.data_frame
    def selected_cars():
        return render.DataGrid(cars.iloc[selection()])


app = App(app_ui, server)
