# Issue #101 repro: marker popup with HTML child (ipywidgets 8), plus a
# session-retained popup whose style is materialized by a temporary borrower's
# default factory.
from ipyleaflet import Map, Marker
from ipywidgets import HTML
from ipywidgets.widgets.widget_string import HTMLStyle
from shiny import App, Inputs, Outputs, Session, reactive, render, ui
from shinywidgets import output_widget, render_widget, session_lifetime
from shinywidgets._lifecycle import get_lifecycle
from traitlets import default

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("style_lifetime"),
    output_widget("map", height="400px"),
)


def server(input: Inputs, output: Outputs, session: Session) -> None:
    counter = reactive.value(0)
    style_origin = reactive.value("")
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
            nonlocal shared_popup
            if shared_popup is None:
                with session_lifetime():
                    shared_popup = HTML(value="shared popup")
            donor = BorrowedStyleHTML(shared_popup)
            style = donor.style
            style_origin.set(
                get_lifecycle(session.root_scope())
                .records[style.model_id]
                .lifetime.kind
            )
            style.text_color = "red" if n % 2 else "blue"
            shared_popup.value = f"shared popup {n}"
            marker.popup = shared_popup
        m.add(marker)
        return m

    @render.text
    def style_lifetime() -> str:
        return style_origin.get()


class BorrowedStyleHTML(HTML):
    def __init__(self, popup: HTML) -> None:
        self.popup = popup
        super().__init__()

    @default("style")
    def style_default(self) -> HTMLStyle:
        return self.popup.style


app = App(app_ui, server)
