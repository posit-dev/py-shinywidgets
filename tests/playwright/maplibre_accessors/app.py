from __future__ import annotations

from maplibre import Map, MapOptions
from shiny import App, render, ui
from shinywidgets import output_widget, render_maplibre

app_ui = ui.page_fillable(
    ui.card(
        output_widget("map"),
        height="500px",
    ),
    ui.input_action_button("rerender", "Re-render"),
    ui.output_text("view_state_out"),
    ui.output_text("clicked_out"),
    ui.output_text("drawn_out"),
)


def server(input, output, session):
    @render_maplibre
    def map():
        input.rerender()
        m = Map(MapOptions(center=(2.3522, 48.8566), zoom=11))
        m.add_mapbox_draw()
        return m

    @render.text
    def view_state_out():
        vs = map.view_state()
        return f"zoom={vs['zoom']:.2f} center=({vs['center']['lng']:.3f},{vs['center']['lat']:.3f})"

    @render.text
    def clicked_out():
        c = map.clicked()
        return "none" if c is None else f"clicked=({c['lng']:.3f},{c['lat']:.3f})"

    @render.text
    def drawn_out():
        return f"{len(map.drawn_features())} feature(s)"


app = App(app_ui, server)
