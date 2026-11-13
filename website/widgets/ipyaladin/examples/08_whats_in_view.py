import numpy as np
import pandas as pd
from ipyaladin import Aladin
from shiny.express import render, ui
from shinywidgets import render_ipyaladin

MESSIER = pd.DataFrame(
    {
        "name": ["M31", "M42", "M45", "M1", "M13", "M51", "M57", "M81", "M27", "M33"],
        "ra": [10.685, 83.822, 56.75, 83.633, 250.423, 202.47, 283.396, 148.888, 299.902, 23.462],
        "dec": [41.269, -5.391, 24.12, 22.014, 36.46, 47.195, 33.029, 69.065, 22.721, 30.66],
        "type": [
            "Galaxy", "Nebula", "Open cluster", "Supernova remnant", "Globular cluster",
            "Galaxy", "Planetary nebula", "Galaxy", "Planetary nebula", "Galaxy",
        ],
    }
)

ui.page_opts(title="target()/fov(): what's in view", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_ipyaladin
        def sky():
            return Aladin(target=(60, 20), fov=90)

    with ui.card():
        ui.card_header("Messier objects in the current view")

        @render.data_frame
        def in_view():
            center, radius = sky.target(), sky.fov().deg / 2
            dist = np.hypot(
                (MESSIER["ra"] - center.ra.deg) * np.cos(np.radians(center.dec.deg)),
                MESSIER["dec"] - center.dec.deg,
            )
            return MESSIER[dist <= radius].reset_index(drop=True)
