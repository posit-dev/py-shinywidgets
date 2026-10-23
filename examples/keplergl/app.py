import numpy as np
import pandas as pd
from shiny import App, render, ui
from shinywidgets import output_widget, reactive_read, render_keplergl

rng = np.random.default_rng(42)

# Synthetic "sensor" readings clustered around a few US cities
cities = {
    "San Francisco": (37.77, -122.42),
    "Chicago": (41.88, -87.63),
    "New York": (40.71, -74.01),
    "Austin": (30.27, -97.74),
}
readings = pd.concat(
    [
        pd.DataFrame(
            {
                "city": city,
                "latitude": lat + rng.normal(0, 0.15, 400),
                "longitude": lon + rng.normal(0, 0.15, 400),
                "reading": rng.gamma(2.0, 10.0, 400).round(1),
            }
        )
        for city, (lat, lon) in cities.items()
    ],
    ignore_index=True,
)

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_checkbox_group(
            "cities", "Cities", choices=list(cities), selected=list(cities)
        ),
        ui.input_slider("min_reading", "Minimum reading", 0, 50, 0),
        ui.output_text("n_layers"),
    ),
    ui.card(output_widget("map"), full_screen=True),
    title="kepler.gl in Shiny",
    fillable=True,
)


def server(input, output, session):
    @render_keplergl
    def map():
        keep = readings["city"].isin(input.cities()) & (
            readings["reading"] >= input.min_reading()
        )
        return readings[keep]

    @render.text
    def n_layers():
        # kepler.gl syncs its config (including layers you add or edit in its
        # side panel) back to Python
        config = reactive_read(map.widget, "config")
        layers = config.get("config", {}).get("visState", {}).get("layers", [])
        return f"Layers in the map: {len(layers)}"


app = App(app_ui, server)
