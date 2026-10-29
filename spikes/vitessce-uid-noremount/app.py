# Spike: verify the maintainer's suggested pattern on vitessce-python#524:
# `remount_on_uid_change=False` + editing a copy of the SYNCED `_config` +
# bumping `uid`. Uses the STOCK VitessceWidget -- no ESM patch, no plugin.
#
# Hypothesis (from reading vit-s source):
#   - `configKey = config.uid ?? JSON.stringify(config)` always changes on a
#     uid bump, and VitessceGrid's `useEffect([success, configKey])` adopts
#     the new config IN PLACE via `setViewConfig()` -- `remountOnUidChange`
#     only controls whether ViewConfigProvider also gets a React `key`
#     (full remount).
#   - Because `_config` syncs the user's current zoom/pan/selections back to
#     Python on every interaction, building the new config from the synced
#     `_config` carries the viewport state across the update.
#
# What to check in the browser:
#   1. Zoom a spatial view, then change the gene: zoom survives (vs. the
#      remount path in examples/vitessce/, where it resets).
#   2. featureSelection echoes back to `_config` (sidebar readout updates).
#   3. No update loop (update counter increments exactly once per pick).
#   4. Watch network/console for data refetch (uid bump recreates the
#      queryClient via `useMemo([configKey])`, so cache is likely busted).
#
# Run with:
#   uv run --with json5 shiny run spikes/vitessce-uid-noremount/app.py
#
# Requires an internet connection (config + zarr data + viewer JS remote).
import copy
import re
import urllib.request
import uuid

from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_vitessce

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
    return cfg


CFG = load_config()

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select("gene", "Color right view by gene (uid bump, no remount)", GENES),
        ui.hr(),
        ui.tags.small(ui.output_text_verbatim("view_state")),
        width=320,
    ),
    ui.card(
        ui.card_header("remount_on_uid_change=False + uid bump spike (vitessce-python#524)"),
        output_widget("vit", height="640px"),
        full_screen=True,
    ),
    title="Vitessce uid-bump no-remount spike",
)


def server(input, output, session):
    @render_vitessce
    def vit():
        from vitessce import VitessceConfig

        vc = VitessceConfig.from_dict(CFG)
        # The one ingredient the maintainer pointed at.
        return vc.widget(height=640, remount_on_uid_change=False)

    update_count = reactive.value(0)

    @render.text
    def view_state():
        cs = reactive_read(vit.widget, "_config").get("coordinationSpace", {})

        def first(name):
            v = list(cs.get(name, {}).values())
            return v[0] if v else None

        zoom = first("spatialZoom")
        return (
            f"spatialZoom: {zoom if zoom is None else round(zoom, 2)}\n"
            f"featureSelection: {first('featureSelection')}\n"
            f"gene updates applied: {update_count()}"
        )

    @reactive.effect
    @reactive.event(input.gene, ignore_init=True)
    def _():
        # Same edit pattern as examples/vitessce/, but built from the SYNCED
        # `_config` (which carries the user's current zoom/pan/selections) and
        # adopted in place thanks to remount_on_uid_change=False.
        new = copy.deepcopy(vit.widget._config)
        new["coordinationSpace"]["featureSelection"]["A"] = [input.gene()]
        new["uid"] = str(uuid.uuid4())[:8]
        vit.widget._config = new
        update_count.set(update_count() + 1)


app = App(app_ui, server)
