# Vitessce dashboard template: public 10x Visium config, a gene picker that
# recolors in place (no viewport reset), and a live readout of what the user
# is looking at (pan/zoom + selected cell sets). Adapt by swapping CONFIG_URL
# for your own VitessceConfig and GENES for your own feature list.
# bucket: template
# run: uv run --no-sync python -m shiny run gallery/template_dashboard.py
# data: public 10x Genomics Visium human lymph node (vitessce.io demo data, MIT)
import copy
import re
import urllib.request
import uuid

from shiny import reactive
from shiny.express import input, render, ui
from vitessce import VitessceConfig

from shinywidgets import reactive_read, render_vitessce

ui.page_opts(title="Vitessce dashboard template", fillable=True)

CONFIG_URL = (
    "https://raw.githubusercontent.com/vitessce/vitessce/main/examples/configs/"
    "src/view-configs/human_lymph_node_10x_visium.js"
)
GENES = ["CR2", "CD3E", "CD3D", "MS4A1", "GNLY", "LYZ", "KRT14", "PECAM1"]


def load_demo_config() -> dict:
    import json5

    src = urllib.request.urlopen(CONFIG_URL, timeout=30).read().decode()
    src = re.sub(r"^export const \w+ = ", "", src).rstrip().rstrip(";")
    cfg = json5.loads(src)
    for d in cfg["datasets"]:
        d.setdefault("name", d["uid"])
    return cfg


CFG = load_demo_config()

with ui.sidebar(width=300):
    ui.input_select("gene", "Color right view by gene", GENES)
    ui.hr()

    @render.code
    def view_state():
        cs = reactive_read(vit.widget, "_config").get("coordinationSpace", {})

        def first(name):
            values = list(cs.get(name, {}).values())
            return values[0] if values else None

        zoom = first("spatialZoom")
        n_sets = len(first("obsSetSelection") or [])
        return (
            f"spatialZoom: {zoom if zoom is None else round(zoom, 2)}\n"
            f"featureSelection: {first('featureSelection')}\n"
            f"obsSetSelection: {n_sets} sets selected"
        )


with ui.card(full_screen=True):
    ui.card_header("Human lymph node, 10x Visium (Vitessce + shinywidgets)")

    @render_vitessce
    def vit():
        return VitessceConfig.from_dict(CFG).widget(remount_on_uid_change=False)


@reactive.effect
@reactive.event(input.gene)
def _():
    # remount_on_uid_change=False (above) keeps the same canvases in place;
    # the uid bump still applies the edit (see "Updating the widget from
    # Python" in the guide for the tradeoffs vs. the default remount).
    new_config = copy.deepcopy(vit.widget._config)
    new_config["coordinationSpace"]["featureSelection"]["A"] = [input.gene()]
    new_config["uid"] = str(uuid.uuid4())[:8]
    vit.widget._config = new_config
