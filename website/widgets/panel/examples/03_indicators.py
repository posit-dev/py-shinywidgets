import panel as pn
from shiny.express import ui
from shinywidgets import render_panel

# Gauge is ECharts-backed; its JS loads through pn.extension() like any
# other extension-bundled pane.
pn.extension("echarts")

ui.page_opts(title="Panel indicators", fillable=True)

with ui.layout_columns(col_widths=[3, 3, 3, 3]):
    with ui.card():
        ui.card_header("Dial")

        @render_panel
        def dial():
            return pn.indicators.Dial(
                name="CPU", value=72, bounds=(0, 100), format="{value}%",
                colors=[(0.6, "green"), (0.85, "gold"), (1, "red")],
                sizing_mode="stretch_both",
            )

    with ui.card():
        ui.card_header("Gauge (ECharts)")

        @render_panel
        def gauge():
            return pn.indicators.Gauge(
                name="Load", value=64, bounds=(0, 100), sizing_mode="stretch_both",
            )

    with ui.card():
        ui.card_header("Number")

        @render_panel
        def number():
            return pn.indicators.Number(
                name="Monthly revenue", value=4239, format="${value:,.0f}",
                colors=[(5000, "red"), (10000, "green")],
                sizing_mode="stretch_both",
            )

    with ui.card():
        ui.card_header("Progress")

        @render_panel
        def progress():
            return pn.indicators.Progress(
                name="Deploy progress", value=64, sizing_mode="stretch_width",
                bar_color="success",
            )
