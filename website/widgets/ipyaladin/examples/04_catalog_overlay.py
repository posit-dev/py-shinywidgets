from astropy.table import Table
from ipyaladin import Aladin
from shiny.express import ui
from shinywidgets import render_ipyaladin

# The seven bright stars of the Pleiades (real coordinates and V magnitudes)
PLEIADES = Table(
    {
        "name": ["Alcyone", "Atlas", "Electra", "Maia", "Merope", "Taygeta", "Pleione"],
        "ra": [56.871, 56.978, 56.216, 56.579, 56.752, 56.447, 56.751],
        "dec": [24.105, 24.054, 24.113, 24.367, 23.948, 24.467, 24.137],
        "vmag": [2.87, 3.62, 3.70, 3.87, 4.17, 4.30, 5.09],
    }
)

ui.page_opts(title="Overlay a catalog", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("The Pleiades (M45), with its seven brightest stars overlaid")

    @render_ipyaladin
    def sky():
        aladin = Aladin(target=(56.75, 24.12), fov=1.2)
        aladin.add_table(PLEIADES, shape="circle", source_size=14, color="#ffd166")
        return aladin
