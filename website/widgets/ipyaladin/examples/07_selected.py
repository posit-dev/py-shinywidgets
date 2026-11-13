import pandas as pd
from astropy.table import Table
from ipyaladin import Aladin
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import reactive_read, render_ipyaladin

PLEIADES = Table(
    {
        "name": ["Alcyone", "Atlas", "Electra", "Maia", "Merope", "Taygeta", "Pleione"],
        "ra": [56.871, 56.978, 56.216, 56.579, 56.752, 56.447, 56.751],
        "dec": [24.105, 24.054, 24.113, 24.367, 23.948, 24.467, 24.137],
        "vmag": [2.87, 3.62, 3.70, 3.87, 4.17, 4.30, 5.09],
    }
)

ui.page_opts(title="selected(): box-select sources", fillable=True)
ui.input_action_button("arm", "Arm rectangle selection")

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_ipyaladin
        def sky():
            aladin = Aladin(target=(56.871, 24.105), fov=1.2)
            aladin.add_table(PLEIADES, shape="circle", source_size=16, color="#ffd166")
            return aladin

        @reactive.effect
        def _():
            w = sky.widget
            if input.arm() > 0 and w and reactive_read(w, "_is_loaded"):
                w.selection("rectangle")

    with ui.card():
        ui.card_header("Stars inside the selection")

        @render.data_frame
        def table():
            tables = sky.selected()
            if not tables:
                return pd.DataFrame({"name": [], "vmag": []})
            return tables[0].to_pandas()[["name", "vmag"]]
