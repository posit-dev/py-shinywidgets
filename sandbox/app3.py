import plotly.graph_objects as go
from shiny import App, ui
from shinywidgets import output_widget, render_plotly
app_ui = ui.page_sidebar(ui.sidebar("x"), ui.card(ui.card_header("h"), output_widget("p"), full_screen=True), title="t")
def server(input, output, session):
    @render_plotly
    def p():
        return go.Figure(go.Scatter(x=[1,2],y=[1,2]))
app = App(app_ui, server)
