from maplibre import Map, MapOptions
from maplibre.basemaps import Carto
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_maplibre

ui.page_opts(fillable=True)

with ui.layout_columns():
    with ui.card():
        ui.card_header("Default: every view_state change")

        @render_maplibre
        def fast():
            return Map(MapOptions(style=Carto.DARK_MATTER, center=(2.3522, 48.8566), zoom=11))

        @render.text
        def fast_count():
            return f"{n_fast.get()} reads"

    with ui.card():
        ui.card_header("rate_delay=1 (debounced)")

        @render_maplibre(rate_policy="debounce", rate_delay=1)
        def slow():
            return Map(MapOptions(style=Carto.DARK_MATTER, center=(2.3522, 48.8566), zoom=11))

        @render.text
        def slow_count():
            return f"{n_slow.get()} reads"


n_fast = reactive.value(0)
n_slow = reactive.value(0)


@reactive.effect
def _count_fast():
    fast.read("view_state")
    # isolate(): reading n_fast here must not make this effect depend on
    # itself -- that would make .set() below re-trigger it forever
    with reactive.isolate():
        n_fast.set(n_fast.get() + 1)


@reactive.effect
def _count_slow():
    slow.read("view_state")
    with reactive.isolate():
        n_slow.set(n_slow.get() + 1)
