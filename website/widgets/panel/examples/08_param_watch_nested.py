import panel as pn
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_panel

ui.page_opts(title="A nested widget: param(name) can't reach it", fillable=True)

quantity = reactive.value(10)

with ui.layout_columns(col_widths=[6, 6]):
    with ui.card():
        ui.card_header("A slider + reset button, returned as one pn.Row")

        @render_panel
        def controls():
            slider = pn.widgets.IntSlider(name="Quantity", value=10, start=0, end=100)
            reset = pn.widgets.Button(name="Reset to 10")
            # controls.param("value") can't reach the slider: the rendered
            # object is the Row, which has no "value" of its own. Watch the
            # nested widget directly instead.
            slider.param.watch(lambda e: quantity.set(e.new), "value")
            reset.on_click(lambda _: setattr(slider, "value", 10))
            return pn.Row(slider, reset)

    with ui.card():
        ui.card_header("quantity (a Shiny reactive.value, set by the watcher)")

        @render.text
        def readout():
            return f"quantity = {quantity()}"
