# Drive the viewer from a Shiny input: pick a gene, the right-hand spatial
# view recolors in place. Requires an internet connection.
import copy
import re
import urllib.request
import uuid

from shiny import reactive
from shiny.express import input, ui
from vitessce import VitessceConfig

from shinywidgets import render_vitessce

ui.page_opts(title="Vitessce: gene picker", fillable=True)

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

with ui.sidebar():
    ui.input_select("gene", "Color right view by gene", GENES)

with ui.card(full_screen=True):

    @render_vitessce
    def vit():
        return VitessceConfig.from_dict(CFG)


# The Vitessce viewer applies a new `_config` by remounting, keyed on the
# config's top-level `uid` -- the viewer assigns one on mount and echoes it
# back, so the bump below is required (without it, the write is a no-op).
# Because the new config is a deep copy of the *live*, already-synced
# `_config`, the current pan/zoom/selections are preserved even though the
# viewer remounts to apply the edit.
@reactive.effect
@reactive.event(input.gene)
def _():
    new_config = copy.deepcopy(vit.widget._config)
    new_config["coordinationSpace"]["featureSelection"]["A"] = [input.gene()]
    new_config["uid"] = str(uuid.uuid4())[:8]
    vit.widget._config = new_config
