# Vitessce in Shiny for Python — human lymph node, 10x Visium
#
# A coordinated multi-view single-cell/spatial viewer (spatial spots colored
# by cluster + by gene expression, heatmap, gene list, cell sets, layer
# controller) rendered from PUBLIC remote zarr data, with live two-way
# reactivity: pick a gene in the sidebar and the viewer updates in place;
# pan/zoom/lasso in the viewer and the readout below follows.
#
# Data: 10x Genomics Visium human lymph node, served by the Vitessce project
# (https://data-1.vitessce.io). Config adapted from the official vitessce
# demo (examples/configs human_lymph_node_10x_visium, MIT). Requires an
# internet connection (config + zarr data + viewer JavaScript are remote).
import copy
import re
import urllib.request

from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_vitessce

CONFIG_URL = "https://raw.githubusercontent.com/vitessce/vitessce/main/examples/configs/src/view-configs/human_lymph_node_10x_visium.js"
GENES = ["CR2", "CD3E", "CD3D", "MS4A1", "GNLY", "LYZ", "KRT14", "PECAM1"]


def load_config():
    """Fetch the demo view config (a JS module) and parse it as a dict."""
    import json5

    src = urllib.request.urlopen(CONFIG_URL).read().decode()
    src = re.sub(r"^export const \w+ = ", "", src).rstrip().rstrip(";")
    cfg = json5.loads(src)
    for d in cfg["datasets"]:
        d.setdefault("name", d["uid"])  # VitessceConfig.from_dict needs it
    return cfg


CFG = load_config()

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select("gene", "Color right view by gene", GENES),
        ui.input_dark_mode(mode="light"),
        ui.hr(),
        ui.tags.small(ui.output_text_verbatim("view_state")),
        width=300,
    ),
    ui.card(
        ui.card_header(
            "Human lymph node, 10x Visium — 3,861 spots (Vitessce + shinywidgets)"
        ),
        output_widget("vit", height="640px"),
        full_screen=True,
    ),
    title="Vitessce in Shiny",
)


def server(input, output, session):
    @render_vitessce
    def vit():
        from vitessce import VitessceConfig

        # A VitessceConfig is coerced via .widget() for us; return
        # config.widget(theme=..., height=...) yourself to control those.
        return VitessceConfig.from_dict(CFG)

    # Browser -> Python: every pan/zoom/selection syncs the whole view config
    # back to the `_config` trait; reactive_read makes it a Shiny input.
    @render.text
    def view_state():
        cs = reactive_read(vit.widget, "_config").get("coordinationSpace", {})

        def first(name):
            v = list(cs.get(name, {}).values())
            return v[0] if v else None

        zoom = first("spatialZoom")
        sel = first("obsSetSelection")
        n_sets = len(sel) if isinstance(sel, list) else 0
        return (
            f"spatialZoom: {zoom if zoom is None else round(zoom, 2)}\n"
            f"spatialTarget: ({first('spatialTargetX')}, {first('spatialTargetY')})\n"
            f"featureSelection: {first('featureSelection')}\n"
            f"obsSetSelection: {n_sets} sets"
        )

    # Python -> browser: rewrite featureSelection in a copy of the config and
    # reassign the `_config` trait. NOTE: the Vitessce viewer only applies a
    # new config prop when its top-level `uid` changes (remountOnUidChange),
    # so bump `uid` -- this remounts the viewer (view state resets, data is
    # re-fetched from cache). Without it, the write is a no-op in the browser.
    @reactive.effect
    @reactive.event(input.gene)
    def _():
        import uuid

        new = copy.deepcopy(vit.widget._config)
        new["coordinationSpace"]["featureSelection"]["A"] = [input.gene()]
        new["uid"] = str(uuid.uuid4())[:8]
        vit.widget._config = new


app = App(app_ui, server)
