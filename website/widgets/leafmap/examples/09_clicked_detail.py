# Needs pandas: `uv run --with pandas shiny run 09_clicked_detail.py`.
import leafmap
import numpy as np
import pandas as pd
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_leafmap

CITIES = pd.read_csv(
    "https://raw.githubusercontent.com/opengeos/leafmap/master/examples/data/world_cities.csv"
)

ui.page_opts(title="Click a city", fillable=True)

with ui.layout_columns(col_widths=(9, 3)):

    @render_leafmap
    def map():
        m = leafmap.Map(center=(20, 0), zoom=2)
        m.add_points_from_xy(CITIES, x="longitude", y="latitude", layer_name="Cities")
        return m

    with ui.card():
        ui.card_header("Nearest city to your last click")

        @render.express
        def detail():
            clicked = map.clicked()
            # req() returns its argument, and render.express treats every bare
            # top-level expression as UI, so assign it rather than leave it bare
            clicked = req(clicked)  # None until the first click
            lat, lng = clicked["coordinates"]
            d2 = (CITIES.latitude - lat) ** 2 + (CITIES.longitude - lng) ** 2
            city = CITIES.loc[np.argmin(d2)]
            ui.markdown(f"**{city['name']}**")
            ui.div(f"Population: {city['pop_max']:,}")
            ui.div(f"({lat:.2f}, {lng:.2f})")
