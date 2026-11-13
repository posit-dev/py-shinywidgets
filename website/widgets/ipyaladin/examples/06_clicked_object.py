from astropy.table import Table
from ipyaladin import Aladin
from shiny.express import render, ui
from shinywidgets import render_ipyaladin

PLEIADES = Table(
    {
        "name": ["Alcyone", "Atlas", "Electra", "Maia", "Merope", "Taygeta", "Pleione"],
        "ra": [56.871, 56.978, 56.216, 56.579, 56.752, 56.447, 56.751],
        "dec": [24.105, 24.054, 24.113, 24.367, 23.948, 24.467, 24.137],
        "vmag": [2.87, 3.62, 3.70, 3.87, 4.17, 4.30, 5.09],
    }
)

ui.page_opts(title="clicked_object(): click a source for detail", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_ipyaladin
        def sky():
            # Centered on Alcyone, the cluster's brightest star
            aladin = Aladin(target=(56.871, 24.105), fov=1.2)
            aladin.add_table(PLEIADES, shape="circle", source_size=16, color="#ffd166")
            return aladin

    with ui.card():
        ui.card_header("Clicked star")

        @render.code
        def detail():
            clicked = sky.clicked_object()
            if clicked is None:
                return "Click a star to see its catalog row."
            return "\n".join(f"{k}: {v}" for k, v in clicked["data"].items())
