import datetime as dt

import hvplot.pandas  # noqa: F401
import pandas as pd
import panel as pn
from shiny import App, Inputs, Outputs, Session, ui
from shinywidgets import output_widget, render_holoviews, render_panel

df = pd.DataFrame(
    {
        "int": [1, 2, 3],
        "float": [3.14, 6.28, 9.42],
        "str": ["A", "B", "C"],
        "date": [dt.date(2019, 1, 1), dt.date(2020, 1, 1), dt.date(2020, 1, 10)],
    },
)

plot_df = pd.DataFrame({"x": [1, 2, 3, 4], "y": [1, 4, 9, 16]})

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender table"),
    output_widget("tabulator"),
    output_widget("hvplot"),
    output_widget("perspective"),
)


def server(input: Inputs, output: Outputs, session: Session) -> None:
    @output(id="tabulator")
    @render_panel
    def _():
        return pn.widgets.Tabulator(
            df.assign(int=df["int"] + input.rerender()), theme="simple"
        )

    @output(id="hvplot")
    @render_holoviews
    def _():
        return plot_df.hvplot.scatter(x="x", y="y")

    @output(id="perspective")
    @render_panel
    def _():
        return pn.pane.Perspective(plot_df)


app = App(app_ui, server)
