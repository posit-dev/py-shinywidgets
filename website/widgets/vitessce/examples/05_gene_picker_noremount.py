# Same gene-picker recipe as 04_gene_picker_inplace.py, but with
# remount_on_uid_change=False: the viewer adopts the new config without
# tearing down and recreating its canvases. Verified: identical zoom
# preservation, but about 1/3 the data-server requests on each edit (23-27
# vs 82 in a measured run) and no DOM teardown (same <canvas> elements
# survive the update). Requires an internet connection.
#
# Caveat (upstream, vitessce/vitessce#2684): this in-place adoption path
# stores the raw config prop, skipping schema upgrade/initialization. Only
# write configs derived from the live, already-synced `_config` (as below) --
# never a freshly built or pristine VitessceConfig -- or the viewer can
# silently fail to render.
import copy
import re
import urllib.request
import uuid

from shiny import reactive
from shiny.express import input, ui
from vitessce import VitessceConfig

from shinywidgets import render_vitessce

ui.page_opts(title="Vitessce: gene picker (no remount)", fillable=True)

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
        return VitessceConfig.from_dict(CFG).widget(remount_on_uid_change=False)


@reactive.effect
@reactive.event(input.gene)
def _():
    new_config = copy.deepcopy(vit.widget._config)
    new_config["coordinationSpace"]["featureSelection"]["A"] = [input.gene()]
    new_config["uid"] = str(uuid.uuid4())[:8]
    vit.widget._config = new_config
