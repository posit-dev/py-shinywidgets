from ipyaladin import Aladin
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_ipyaladin

ui.page_opts(title="Rate-limited target()/fov()", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_ipyaladin(rate_policy="debounce", rate_delay=0.3)
        def sky():
            return Aladin(target=(83.63, 22.01), fov=5)

    with ui.card():
        ui.card_header("Pans/zooms seen by Python (debounced to 1 per 300 ms)")
        count = reactive.value(0)

        @reactive.effect
        def _count():
            sky.target()
            sky.fov()
            with reactive.isolate():
                count.set(count() + 1)

        @render.text
        def n():
            return f"updates received: {count()}"
