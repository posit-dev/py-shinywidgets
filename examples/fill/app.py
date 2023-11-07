import altair as alt
import ipyleaflet as leaflet
import plotly.express as px
import pydeck as pdk
from shiny import App, ui
from vega_datasets import data

from shinywidgets import output_widget, register_widget

# altair setup
brush = alt.selection_point(name="point", encodings=["color"], bind="legend")
chart = alt.Chart(data.cars()).mark_point().encode(
    x='Horsepower:Q',
    y='Miles_per_Gallon:Q',
    color=alt.condition(brush, 'Origin:N', alt.value('grey')),
).add_params(brush)

# pydeck setup
UK_ACCIDENTS_DATA = "https://raw.githubusercontent.com/visgl/deck.gl-data/master/examples/3d-heatmap/heatmap-data.csv"
layer = pdk.Layer(
    "HexagonLayer",
    UK_ACCIDENTS_DATA,
    get_position=["lng", "lat"],
    auto_highlight=True,
    elevation_scale=50,
    pickable=True,
    elevation_range=[0, 3000],
    extruded=True,
    coverage=1,
)
view_state = pdk.ViewState(
    longitude=-1.415,
    latitude=52.2323,
    zoom=6,
    min_zoom=5,
    max_zoom=15,
    pitch=40.5,
    bearing=-27.36,
)

def card_output(id):
    return ui.card(
        ui.card_header(id),
        output_widget(id),
        full_screen=True,
    )


app_ui = ui.page_fillable(
    ui.layout_column_wrap(
        card_output("plotly"),
        card_output("altair"),
        width=1 / 2
    ),
    ui.layout_column_wrap(
        card_output("ipyleaflet"),
        card_output("pydeck"),
        width=1 / 2
    ),
)

def server(input, output, session):
    WIDGETS = {
        "plotly": px.scatter(data.cars(), x="Horsepower", y="Miles_per_Gallon", color="Origin"),
        "altair": chart,
        "ipyleaflet": leaflet.Map(center=(52.204793, 360.121558), zoom=8),
        "pydeck": pdk.Deck(layers=[layer], initial_view_state=view_state),
    }
    register_widget("plotly", WIDGETS["plotly"])
    # register_widget("plotly2", WIDGETS["plotly"])
    register_widget("altair", WIDGETS["altair"])
    # register_widget("altair2", WIDGETS["altair"])
    register_widget("ipyleaflet", WIDGETS["ipyleaflet"])
    register_widget("pydeck", WIDGETS["pydeck"])

app = App(app_ui, server)
