from __future__ import annotations

import panel as pn
from shiny import App, ui
from shinywidgets import output_widget, render_panel

# ECharts-backed components (pn.pane.ECharts, pn.indicators.Gauge) render
# blank unless the echarts extension's JS is loaded with the page
pn.extension("echarts")

app_ui = ui.page_fluid(
    output_widget("chart"),
    output_widget("gauge"),
)


def server(input, output, session):
    @render_panel
    def chart():
        return pn.pane.ECharts(
            {
                "xAxis": {"type": "category", "data": ["a", "b", "c"]},
                "yAxis": {"type": "value"},
                "series": [{"type": "bar", "data": [1, 2, 3]}],
            },
            height=300,
            sizing_mode="stretch_width",
        )

    @render_panel
    def gauge():
        # Gauge is ECharts-backed too
        return pn.indicators.Gauge(
            name="Load", value=64, bounds=(0, 100), width=300, height=250
        )


app = App(app_ui, server)
