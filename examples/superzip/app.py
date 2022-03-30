import os
from htmltools import head_content
from shiny import *
from ipyshiny import output_widget, render_widget
import ipyleaflet as leaflet
from ipyleaflet import basemaps
import pandas as pd

app_dir = os.path.dirname(__file__)
allzips = pd.read_csv(os.path.join(app_dir, "superzip.csv"))
allzips.sample(n=10000, random_state=42)


vars = {
    "superzip": "Is SuperZIP?",
    "centile": "Centile score",
    "college": "College education",
    "income": "Median income",
    "adultpop": "Population",
}

css = open(os.path.join(app_dir, "styles.css"), "r").readlines()

ui_map = ui.TagList(
    output_widget("map", width="100%", height="100%"),
    ui.panel_fixed(
        # TODO: how to handle HTML inside the JSX Tag?!?!?
        ui.h2(ui.HTML("ZIP explorer<br/>(no tiles)")),
        ui.input_select("color", "Color", vars),
        ui.input_select("size", "Size", vars, selected="adultpop"),
        ui.panel_conditional(
            "input.color == 'superzip' || input.size == 'superzip'",
            ui.input_numeric("threshold", "SuperZIP threshold (top n percentile)", 5),
        ),
        ui.output_plot("histCentile", height=200),
        ui.output_plot("scatterCollegeIncome", height=250),
        id="controls",
        class_="panel panel-default",
        width="330px",
        height="auto",
        draggable=True,
        top="60px",
        left="auto",
        right="20px",
        bottom="auto",
    ),
    ui.div(
        "Data compiled for ",
        ui.tags.em("Coming Apart: The State of White America, 1960-2010"),
        " by Charles Murray (Crown Forum, 2012).",
        id="cite",
    ),
)

app_ui = ui.page_navbar(
    ui.nav(
        "Interactive map",
        ui.div(head_content(ui.tags.style(css)), ui_map, class_="outer"),
    ),
    ui.nav(
        "Data explorer",
        ui.row(
            ui.column(
                3,
                ui.input_select(
                    "states",
                    "States",
                    {"": "All states"},
                    # structure(state.abb, names=state.name), "Washington, DC"="DC"),
                    multiple=True,
                ),
            ),
            ui.column(
                3,
                ui.panel_conditional(
                    "input.states",
                    ui.input_select(
                        "cities", "Cities", {"": "All cities"}, multiple=True
                    ),
                ),
            ),
            ui.column(
                3,
                ui.panel_conditional(
                    "input.states",
                    ui.input_select(
                        "zipcodes", "Zipcodes", {"": "All zipcodes"}, multiple=True
                    ),
                ),
            ),
        ),
        ui.row(
            ui.column(
                1, ui.input_numeric("minScore", "Min score", min=0, max=100, value=0)
            ),
            ui.column(
                1, ui.input_numeric("maxScore", "Max score", min=0, max=100, value=100)
            ),
        ),
        ui.hr(),
        output_widget("data"),
    ),
    title="Superzip",
)


def server(input: Inputs, output: Outputs, session: Session):

    map = leaflet.Map(center=(37.45, -93.85), zoom=4)
    map.add_layer(leaflet.basemap_to_tiles(basemaps.CartoDB.DarkMatter))
    map.add_control(leaflet.FullScreenControl())

    @output(name="map")
    @render_widget()
    def _():
        return map

    @reactive.Calc()
    def zipsInBounds():
        breakpoint()
        return None

    @output(name="data")
    @render_widget()
    def _():
        return None


app = App(app_ui, server)
