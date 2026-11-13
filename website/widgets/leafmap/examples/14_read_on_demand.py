import leafmap
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_leafmap

ui.page_opts(title="Save the current view on demand", fillable=True)

# Every accessor attaches when the map renders, so this button's reads see
# the user's latest pan or drawn shape with no warm-up read elsewhere in
# the app keeping bounds()/drawn_features() "live" first.
saved = reactive.value([])

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card():
        ui.input_action_button("save", "Save current view", class_="mb-2")

        @render_leafmap
        def map():
            m = leafmap.Map(center=(47.62, -122.33), zoom=11)
            m.add_basemap("Esri.WorldImagery")
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
