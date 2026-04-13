from __future__ import annotations

import plotly.graph_objects as go
from shiny import App, ui
from shinywidgets import output_widget, render_plotly

app_ui = ui.page_fillable(
    ui.tags.div(id="spacer", style="height: 0px; flex: 0 0 auto;"),
    ui.input_checkbox("show_points", "Show points", value=True),
    output_widget("plot"),
    ui.tags.script(
        """
        document.addEventListener("DOMContentLoaded", () => {
          const spacer = document.getElementById("spacer");
          if (!spacer) return;

          [160, 40, 220, 0].forEach((height, i) => {
            setTimeout(() => {
              spacer.style.height = `${height}px`;
            }, 650 + i * 150);
          });
        });
        """
    ),
)


def server(input, output, session):
    @render_plotly
    def plot():
        return go.FigureWidget(
            data=[
                go.Scattergl(
                    x=list(range(1000)),
                    y=list(range(1000)),
                    mode="markers",
                )
            ],
            layout={"showlegend": False},
        )


app = App(app_ui, server)
