# Needs: uv run --no-sync --with ipydeck python -m shiny run 09_third_party_ipydeck.py
#
# A second no-dedicated-renderer example: ipydeck (deck.gl layers as an
# anywidget). Same `render_widget` recipe as mapwidget, but ipydeck has a
# sharp upstream edge worth knowing before you try it: deck.gl's own
# "accessor" properties (`get_position`, `get_fill_color`, ...) only become
# functions when the Python value is a string prefixed `@@=`. A plain column
# name -- which is exactly how pydeck accepts it -- renders nothing, with no
# error anywhere.
from ipydeck import Deck, Layer, ViewState
from shiny.express import render, ui
from shinywidgets import render_widget

CITIES = [
    {"name": "San Francisco", "position": [-122.42, 37.78]},
    {"name": "Oakland", "position": [-122.27, 37.80]},
    {"name": "Berkeley", "position": [-122.27, 37.87]},
    {"name": "San Jose", "position": [-121.89, 37.34]},
]

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header('get_position="@@=position" -- required, not "position"')

        @render_widget
        def deck():
            return Deck(
                layers=[
                    Layer(
                        "ScatterplotLayer",
                        data=CITIES,
                        id="cities",
                        pickable=True,
                        on_click=True,
                        get_position="@@=position",  # plain "position" silently draws nothing
                        get_radius=8000,
                        get_fill_color=[255, 140, 0],
                    )
                ],
                initial_view_state=ViewState(longitude=-122.3, latitude=37.7, zoom=8),
                map_style="dark",
                tooltip={"html": "<b>{name}</b>"},
            )

    with ui.card():
        ui.card_header('deck.read("click") -- the picked object')

        @render.code
        def click_out():
            picked = deck.read("click")
            return "click a city" if not picked else str(picked.get("object"))
