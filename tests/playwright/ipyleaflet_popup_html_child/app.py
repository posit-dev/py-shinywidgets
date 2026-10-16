# Issue #101 repro: marker popup with HTML child (ipywidgets 8), plus a
# session-retained popup whose style is first materialized while a temporary
# map serializes (the borrowed-default case).
from ipyleaflet import Map, Marker
from ipywidgets import HTML
from shiny import App, reactive, ui
from shinywidgets import output_widget, render_widget, session_lifetime

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    output_widget("map", height="400px"),
)


def server(input, output, session):
    counter = reactive.value(0)
    shared_popup: HTML | None = None

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render_widget
    def map():
        n = counter.get()
        m = Map(center=(52.204793 + n * 0.001, 0.121558), zoom=13)
        marker = Marker(location=(52.204793 + n * 0.001, 0.121558), draggable=False)
        if n == 0:
            marker.popup = HTML(value="hello popup #101")
        else:
            # Successive temporary maps borrow the same session-retained
            # popup; its Layout/Style are first materialized while a
            # temporary map serializes.
            nonlocal shared_popup
            if shared_popup is None:
                with session_lifetime():
                    shared_popup = HTML(value="shared popup")
            marker.popup = shared_popup
        m.add(marker)
        return m


app = App(app_ui, server)
