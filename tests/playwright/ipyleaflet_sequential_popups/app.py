# Issue #194: clicking the map twice in sequence should each produce a popup
# whose plotly FigureWidget child renders (previously only the "last" popup
# ever displayed). Adapted from the issue's MRE with a shortened sleep.
import time

import numpy as np
import plotly.graph_objs as go
from ipyleaflet import Map, Popup
from ipywidgets import HTML
from shiny import App, reactive, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fillable(output_widget("map", height="600px"))


def server(input, output, session):
    click_coords = reactive.value((None, None))

    def create_interactive_plot():
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        fig = go.FigureWidget(data=[go.Scatter(x=x, y=y, mode="lines+markers")])
        fig.update_layout(
            title="Interactive Plotly Plot in Popup",
            width=350,
            height=250,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        return fig

    @reactive.effect
    def _():
        lat, lng = click_coords.get()
        if lat is None or lng is None:
            return

        loading_html = HTML()
        loading_html.value = "<b>loading...</b>"

        popup = Popup(
            location=(lat, lng),
            child=loading_html,
            close_button=True,
            auto_close=True,
            close_on_escape_key=True,
        )
        map.widget.add(popup)

        time.sleep(0.5)

        popup.child = create_interactive_plot()

    @render_widget
    def map():
        m = Map(center=(18.5, 116.4), zoom=4.5, scroll_wheel_zoom=True)

        def handle_map_interaction(**kwargs):
            if kwargs.get("type") == "click":
                lat, lon = kwargs.get("coordinates")
                click_coords.set((lat, lon))

        m.on_interaction(handle_map_interaction)
        return m


app = App(app_ui, server)
