# Issue #101 repro: marker popup with HTML child (ipywidgets 8)
from ipyleaflet import Map, Marker
from ipywidgets import HTML
from shiny import App, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fluid(
    output_widget("map", height="400px"),
)


def server(input, output, session):
    @render_widget
    def map():
        m = Map(center=(52.204793, 0.121558), zoom=13)
        marker = Marker(location=(52.204793, 0.121558), draggable=False)
        marker.popup = HTML(value="hello popup #101")
        m.add(marker)
        return m


app = App(app_ui, server)
