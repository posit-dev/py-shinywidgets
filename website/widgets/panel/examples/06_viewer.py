import panel as pn
import param
from shiny.express import ui
from shinywidgets import render_panel


class TemperatureConverter(pn.viewable.Viewer):
    """A reusable component: one widget, one computed display, no Shiny code."""

    celsius = param.Number(default=20, bounds=(-40, 120))

    def __panel__(self):
        slider = pn.widgets.FloatSlider.from_param(self.param.celsius, name="Celsius")
        fahrenheit = pn.bind(lambda c: f"**{c * 9 / 5 + 32:.1f} F**", self.param.celsius)
        return pn.Column(slider, pn.pane.Markdown(fahrenheit))


ui.page_opts(title="pn.viewable.Viewer", fillable=True)

with ui.card():
    ui.card_header("A Viewer bundles widgets + logic into one reusable component")

    @render_panel
    def converter():
        return TemperatureConverter()
