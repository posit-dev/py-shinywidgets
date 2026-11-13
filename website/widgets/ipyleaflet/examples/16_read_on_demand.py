import ipyleaflet as L
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="Save the current view on demand", fillable=True)

# Every accessor attaches when the map renders, so nothing needs to keep
# reading bounds()/drawn_features() for this button's reads to see the
# user's latest pan or shape -- they're there the moment the button is
# clicked, with no warm-up read required first.
saved = reactive.value([])

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card():
        ui.input_action_button("save", "Save current view", class_="mb-2")

        @render_ipyleaflet
        def map():
            m = L.Map(center=(40.73, -73.99), zoom=13)
            m.add(L.DrawControl(polygon={"shapeOptions": {"color": "#2a7fff"}}))
            return m

    with ui.card():
        ui.card_header("Saved views")

        @render.ui
        def views():
            if not saved():
                return "Pan the map, maybe draw a shape, then click Save."
            items = [
                ui.tags.li(f"center={c} zoom={z:.0f} shapes={n}") for c, z, n in saved()
            ]
            return ui.tags.ol(*items)


@reactive.effect
@reactive.event(input.save)
def _save_view():
    saved.set([*saved(), (map.center(), map.zoom(), len(map.drawn_features()))])
