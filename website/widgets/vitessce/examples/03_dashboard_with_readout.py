# A full coordinated dashboard from one public config: two linked spatial
# views (cluster colors + gene expression), a heatmap, gene list, and cell
# sets -- plus a live readout of what the user is looking at.
#
# Data: 10x Genomics Visium human lymph node, served by the Vitessce project
# (https://data-1.vitessce.io). Config adapted from the official vitessce
# demo (examples/configs human_lymph_node_10x_visium, MIT). Requires an
# internet connection (config + zarr data + viewer JS are all remote).
import re
import urllib.request

from shiny.express import render, ui
from vitessce import VitessceConfig

from shinywidgets import reactive_read, render_vitessce

ui.page_opts(title="Vitessce dashboard", fillable=True)

CONFIG_URL = (
    "https://raw.githubusercontent.com/vitessce/vitessce/main/examples/configs/"
    "src/view-configs/human_lymph_node_10x_visium.js"
)


def load_demo_config() -> dict:
    """Fetch the public demo view config (a JS module) and parse it as a dict."""
    import json5

    src = urllib.request.urlopen(CONFIG_URL, timeout=30).read().decode()
    src = re.sub(r"^export const \w+ = ", "", src).rstrip().rstrip(";")
    cfg = json5.loads(src)
    for d in cfg["datasets"]:
        d.setdefault("name", d["uid"])  # VitessceConfig.from_dict() needs it
    return cfg


CFG = load_demo_config()

with ui.layout_sidebar():
    with ui.sidebar():

        @render.code
        def view_state():
            cs = reactive_read(vit.widget, "_config").get("coordinationSpace", {})

            def first(name):
                values = list(cs.get(name, {}).values())
                return values[0] if values else None

            zoom = first("spatialZoom")
            return (
                f"spatialZoom: {zoom if zoom is None else round(zoom, 2)}\n"
                f"featureSelection: {first('featureSelection')}\n"
                f"obsSetSelection: {len(first('obsSetSelection') or [])} sets selected"
            )

    with ui.card(full_screen=True):

        @render_vitessce
        def vit():
            return VitessceConfig.from_dict(CFG)
