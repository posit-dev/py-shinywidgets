# Messier explorer -- all 110 Messier objects on a live Aladin Lite viewer.
# showcase | ~245 lines (most of it is the embedded catalog) |
# run: uv run --with pandas shiny run showcase_messier_explorer.py
# Data: the Messier catalog (public domain; embedded below as a small CSV).
#
# Pan and zoom the sky and the table tracks whatever is in view (target()/
# fov()). Select a table row and the viewer flies there in place. Click a
# marker and Python sees the object (clicked_object()). Box-select a region
# (after arming it) and the sources inside land in a second table
# (selected()). Survey and color map re-skin the viewer in place.
from __future__ import annotations

import io

import numpy as np
import pandas as pd
from astropy.table import Table
from ipyaladin import Aladin
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_ipyaladin

MESSIER_CSV = """name,ra,dec,type,mag
M1,83.633,22.014,Supernova remnant,8.4
M2,323.363,-0.823,Globular cluster,6.5
M3,205.548,28.377,Globular cluster,6.2
M4,245.897,-26.526,Globular cluster,5.9
M5,229.638,2.081,Globular cluster,5.9
M6,265.03,-32.22,Open cluster,4.2
M7,268.47,-34.79,Open cluster,3.3
M8,270.92,-24.38,Nebula,6.0
M9,259.799,-18.516,Globular cluster,7.7
M10,254.288,-4.100,Globular cluster,6.6
M11,282.77,-6.27,Open cluster,6.3
M12,251.809,-1.949,Globular cluster,6.7
M13,250.423,36.460,Globular cluster,5.8
M14,264.401,-3.246,Globular cluster,7.6
M15,322.493,12.167,Globular cluster,6.2
M16,274.70,-13.81,Nebula,6.4
M17,275.11,-16.17,Nebula,6.0
M18,274.99,-17.80,Open cluster,7.5
M19,255.657,-26.268,Globular cluster,6.8
M20,270.60,-23.03,Nebula,6.3
M21,271.13,-22.49,Open cluster,6.5
M22,279.100,-23.906,Globular cluster,5.1
M23,269.05,-18.99,Open cluster,6.9
M24,274.20,-18.50,Star cloud,4.6
M25,277.90,-19.12,Open cluster,6.5
M26,281.33,-9.38,Open cluster,8.0
M27,299.902,22.721,Planetary nebula,7.5
M28,276.137,-24.870,Globular cluster,6.8
M29,305.98,38.52,Open cluster,7.1
M30,325.092,-23.180,Globular cluster,7.2
M31,10.685,41.269,Galaxy,3.4
M32,10.674,40.865,Galaxy,8.1
M33,23.462,30.660,Galaxy,5.7
M34,40.52,42.75,Open cluster,5.5
M35,92.23,24.33,Open cluster,5.3
M36,84.06,34.14,Open cluster,6.3
M37,88.08,32.55,Open cluster,6.2
M38,82.17,35.85,Open cluster,6.4
M39,322.96,48.43,Open cluster,4.6
M40,185.55,58.08,Double star,8.4
M41,101.50,-20.76,Open cluster,4.5
M42,83.822,-5.391,Nebula,4.0
M43,83.87,-5.27,Nebula,9.0
M44,130.10,19.67,Open cluster,3.7
M45,56.75,24.12,Open cluster,1.6
M46,115.43,-14.81,Open cluster,6.1
M47,114.15,-14.50,Open cluster,4.4
M48,123.43,-5.75,Open cluster,5.8
M49,187.445,8.00,Galaxy,8.4
M50,105.69,-8.38,Open cluster,5.9
M51,202.470,47.195,Galaxy,8.4
M52,351.20,61.59,Open cluster,7.3
M53,198.23,18.17,Globular cluster,7.6
M54,283.764,-30.480,Globular cluster,7.6
M55,294.999,-30.965,Globular cluster,6.3
M56,289.148,30.063,Globular cluster,8.3
M57,283.396,33.029,Planetary nebula,8.8
M58,189.43,11.82,Galaxy,9.7
M59,190.51,11.65,Galaxy,9.6
M60,190.917,11.553,Galaxy,8.8
M61,185.479,4.474,Galaxy,9.7
M62,255.303,-30.112,Globular cluster,6.5
M63,198.955,42.029,Galaxy,8.6
M64,194.182,21.683,Galaxy,8.5
M65,169.733,13.092,Galaxy,9.3
M66,170.063,12.991,Galaxy,8.9
M67,132.83,11.81,Open cluster,6.1
M68,189.867,-26.744,Globular cluster,7.8
M69,277.846,-32.348,Globular cluster,7.6
M70,280.803,-32.292,Globular cluster,7.9
M71,298.444,18.779,Globular cluster,8.2
M72,313.365,-12.537,Globular cluster,9.3
M73,314.73,-12.63,Asterism,9.0
M74,24.174,15.783,Galaxy,9.4
M75,301.042,-21.922,Globular cluster,8.5
M76,25.58,51.57,Planetary nebula,10.1
M77,40.670,-0.013,Galaxy,8.9
M78,86.69,0.08,Nebula,8.3
M79,81.04,-24.55,Globular cluster,7.7
M80,244.260,-22.976,Globular cluster,7.3
M81,148.888,69.065,Galaxy,6.9
M82,148.968,69.680,Galaxy,8.4
M83,204.254,-29.866,Galaxy,7.5
M84,186.265,12.887,Galaxy,9.1
M85,186.35,18.19,Galaxy,9.1
M86,186.549,12.946,Galaxy,8.9
M87,187.706,12.391,Galaxy,8.6
M88,187.997,14.420,Galaxy,9.6
M89,188.916,12.556,Galaxy,9.8
M90,189.208,13.163,Galaxy,9.5
M91,188.860,14.496,Galaxy,10.2
M92,259.281,43.136,Globular cluster,6.4
M93,116.11,-23.86,Open cluster,6.0
M94,192.721,41.120,Galaxy,8.2
M95,160.99,11.70,Galaxy,9.7
M96,161.69,11.82,Galaxy,9.2
M97,168.699,55.019,Planetary nebula,9.9
M98,183.451,14.900,Galaxy,10.1
M99,184.707,14.416,Galaxy,9.9
M100,185.729,15.822,Galaxy,9.3
M101,210.802,54.349,Galaxy,7.9
M102,226.62,55.76,Galaxy,9.9
M103,23.34,60.70,Open cluster,7.4
M104,189.998,-11.623,Galaxy,8.0
M105,161.96,12.58,Galaxy,9.3
M106,184.740,47.304,Galaxy,8.4
M107,248.133,-13.054,Globular cluster,7.9
M108,167.879,55.674,Galaxy,10.0
M109,179.400,53.375,Galaxy,9.8
M110,10.092,41.685,Galaxy,8.1
"""

messier = pd.read_csv(io.StringIO(MESSIER_CSV))

SURVEYS = {
    "https://alaskybis.unistra.fr/DSS/DSSColor": "DSS color (optical)",
    "https://alaskybis.unistra.fr/2MASS/Color": "2MASS color (infrared)",
    "https://alaskybis.unistra.fr/AllWISE/Color": "allWISE color (mid-IR)",
}
CMAPS = ["native", "viridis", "cubehelix", "grayscale"]

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select("survey", "Survey", SURVEYS),
        ui.input_select("cmap", "Color map", CMAPS),
        ui.input_action_button("arm_selection", "Arm rectangle selection"),
        ui.p(
            "Drag to pan, scroll to zoom. Click a marker for details, box-select "
            "a region, or pick a table row to fly there.",
            class_="text-muted small",
        ),
        width=280,
    ),
    ui.card(ui.card_header("Messier explorer"), output_widget("sky"), full_screen=True),
    ui.layout_columns(
        ui.card(ui.card_header("In the current view"), ui.output_data_frame("in_view")),
        ui.card(
            ui.card_header("Clicked object"),
            ui.output_code("detail"),
            ui.card_header("Box selection"),
            ui.output_data_frame("selected"),
        ),
        col_widths=[7, 5],
    ),
    title="Messier explorer",
    fillable=True,
)


def server(input, output, session):
    @render_ipyaladin
    def sky():
        aladin = Aladin(survey=list(SURVEYS)[0], target=(56.75, 24.12), fov=5)
        aladin.add_table(
            Table.from_pandas(messier),
            name="messier",
            color="#ffb14e",
            source_size=14,
            shape="square",
        )
        return aladin

    @reactive.effect
    def _survey():
        w = sky.widget
        if w:
            w.survey = input.survey()

    @reactive.effect
    def _cmap():
        w = sky.widget
        if w and reactive_read(w, "_is_loaded") and input.cmap() != "native":
            w.set_color_map(input.cmap())

    @reactive.effect
    def _arm():
        w = sky.widget
        if input.arm_selection() > 0 and w and reactive_read(w, "_is_loaded"):
            w.selection("rectangle")

    @reactive.calc
    def visible():
        center, radius = sky.target(), max(sky.fov().deg, 1.0) / 2
        dist = np.hypot(
            (messier["ra"] - center.ra.deg) * np.cos(np.radians(center.dec.deg)),
            messier["dec"] - center.dec.deg,
        )
        return messier[dist <= radius].sort_values("mag").reset_index(drop=True)

    @render.data_frame
    def in_view():
        return render.DataGrid(visible(), selection_mode="row", width="100%")

    # Selecting a row flies the rendered viewer to the object, in place
    @reactive.effect
    def _fly_to_selected_row():
        rows = input.in_view_selected_rows()
        w = sky.widget
        if not (w and rows and reactive_read(w, "_is_loaded")):
            return
        with reactive.isolate():
            df = visible()
        if not df.empty and rows[0] < len(df):
            row = df.iloc[rows[0]]
            w.target = f"{row.ra} {row.dec}"
            w.fov = 4

    @render.code
    def detail():
        clicked = sky.clicked_object()
        if clicked is None or not clicked.get("data"):
            return "Click a marker in the sky to inspect it."
        return "\n".join(f"{k}: {v}" for k, v in clicked["data"].items())

    @render.data_frame
    def selected():
        tables = sky.selected()
        if not tables:
            return pd.DataFrame({"name": [], "type": [], "mag": []})
        return tables[0].to_pandas()[["name", "type", "mag"]]


app = App(app_ui, server)
