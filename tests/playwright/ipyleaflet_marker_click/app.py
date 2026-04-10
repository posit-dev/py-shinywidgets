from ipyleaflet import Map, Marker
from ipywidgets import Layout
from shiny import App, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_sidebar(
    ui.sidebar("Sidebar content"),
    output_widget("map"),
)


def server(input, output, session):
    def handle_click(**kwargs):
        if kwargs.get("type") == "click":
            map.widget.add_layer(Marker(location=kwargs.get("coordinates")))

    @render_widget
    def map():
        m = Map(
            center=(51.174608, 3.865813),
            zoom=9,
            scroll_wheel_zoom=True,
            layout=Layout(width="80%", height="90vh"),
        )
        m.on_interaction(handle_click)
        return m


app = App(app_ui, server)
