import pandas as pd
import panel as pn
from bokeh.plotting import figure
from panel.viewable import Viewable
from shiny import App, Inputs, Outputs, Session, ui
from shinywidgets import output_widget, render_bokeh, render_panel

app_ui = ui.page_fluid(
    ui.input_action_button("show_markdown", "Show Markdown"),
    ui.input_action_button("show_table", "Show table"),
    output_widget("warm"),
    output_widget("panel_output"),
)


def server(input: Inputs, output: Outputs, session: Session) -> None:
    @render_bokeh
    def warm() -> figure:
        plot = figure(width=300, height=200)
        plot.line([1, 2], [1, 2])
        return plot

    @render_panel
    def panel_output() -> Viewable | None:
        if input.show_table():
            return pn.widgets.Tabulator(pd.DataFrame({"x": [1, 2, 3]}))
        if input.show_markdown():
            return pn.pane.Markdown("# Initial content")
        return None


app = App(app_ui, server)
