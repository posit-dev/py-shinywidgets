# Spike: in-place coordination updates (no viewer remount) via a patched
# VitessceWidget ESM. Same lymph-node demo as examples/vitessce, but the
# gene picker calls widget.set_coordination() instead of reassigning
# `_config` with a uid bump -- the viewer recolors WITHOUT resetting
# zoom/pan/selections.
#
# Run with:
#   uv run --with json5 shiny run spikes/vitessce-inplace/app.py
#
# Requires an internet connection (config + zarr data + viewer JS remote).
import re
import urllib.request

from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_vitessce

from inplace_widget import CoordinationBridgePlugin, InplaceVitessceWidget

CONFIG_URL = "https://raw.githubusercontent.com/vitessce/vitessce/main/examples/configs/src/view-configs/human_lymph_node_10x_visium.js"
GENES = ["CR2", "CD3E", "CD3D", "MS4A1", "GNLY", "LYZ", "KRT14", "PECAM1"]


def load_config():
    """Fetch the demo view config (a JS module) and parse it as a dict."""
    import json5

    src = urllib.request.urlopen(CONFIG_URL, timeout=30).read().decode()
    src = re.sub(r"^export const \w+ = ", "", src).rstrip().rstrip(";")
    cfg = json5.loads(src)
    for d in cfg["datasets"]:
        d.setdefault("name", d["uid"])  # VitessceConfig.from_dict needs it
    # Add the coordination-bridge plugin view as a small panel below the
    # existing layout (plugin views are visual; there is no official
    # non-visual in-tree mount point -- see module docstring).
    bottom = max(v.get("y", 0) + v.get("h", 1) for v in cfg["layout"])
    cfg["layout"].append(
        {"component": "coordination-bridge", "x": 0, "y": bottom, "w": 2, "h": 1}
    )
    return cfg


CFG = load_config()

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select("gene", "Color right view by gene (in-place)", GENES),
        ui.hr(),
        ui.tags.small(ui.output_text_verbatim("view_state")),
        width=300,
    ),
    ui.card(
        ui.card_header("In-place coordination update spike (vitessce-python#524)"),
        output_widget("vit", height="640px"),
        full_screen=True,
    ),
    title="Vitessce in-place spike",
)


def server(input, output, session):
    @render_vitessce
    def vit():
        from vitessce import VitessceConfig

        vc = VitessceConfig.from_dict(CFG)
        return InplaceVitessceWidget(
            vc, height=640, plugins=[CoordinationBridgePlugin()]
        )

    # The bridge writes to the store, which echoes back to `_config` via the
    # usual onConfigChange path -- so this readout reflects bridge updates too.
    @render.text
    def view_state():
        cs = reactive_read(vit.widget, "_config").get("coordinationSpace", {})

        def first(name):
            v = list(cs.get(name, {}).values())
            return v[0] if v else None

        zoom = first("spatialZoom")
        return (
            f"spatialZoom: {zoom if zoom is None else round(zoom, 2)}\n"
            f"featureSelection: {first('featureSelection')}"
        )

    @reactive.effect
    @reactive.event(input.gene, ignore_init=True)
    def _():
        vit.widget.set_coordination("featureSelection", [input.gene()], scope="A")


app = App(app_ui, server)
