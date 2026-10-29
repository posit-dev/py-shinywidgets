# Spike: verify remount_on_uid_change=False is safe as a shinywidgets
# DEFAULT -- i.e., that the in-place adoption path (VitessceGrid's
# setViewConfig effect) handles the update types a Shiny app might make,
# not just the coordination edits the pattern was built for.
#
# Three update types, all with the stock widget + remount_on_uid_change=False:
#   1. Coordination edit (gene picker)     -> expect viewport preserved
#   2. STRUCTURAL change (toggle heatmap)  -> the risk case: views
#      added/removed without a remount; expect graceful adaptation
#   3. Full reset (write pristine config)  -> expect viewport resets to
#      defaults (proves remount-like behavior is still achievable)
#
# Run with:
#   uv run --with json5 shiny run spikes/vitessce-noremount-verify/app.py
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
# The view we'll toggle for the structural-change test.
HEATMAP_VIEW = next(v for v in CFG["layout"] if v["component"] == "heatmap")

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select("gene", "1. Coordination edit (gene)", GENES),
        ui.input_action_button("toggle", "2. Toggle heatmap view (structural)"),
        ui.input_checkbox("freepos", "Re-add at free position (below grid)", False),
        ui.input_action_button("reset", "3. Reset to pristine config"),
        ui.hr(),
        ui.tags.small(ui.output_text_verbatim("view_state")),
        width=320,
    ),
    ui.card(
        ui.card_header("remount_on_uid_change=False default-safety verification"),
        output_widget("vit", height="640px"),
        full_screen=True,
    ),
    title="Vitessce no-remount default verification",
)


def bump_and_write(widget, new):
    new["uid"] = str(uuid.uuid4())[:8]
    widget._config = new


def server(input, output, session):
    @render_vitessce
    def vit():
        from vitessce import VitessceConfig

        vc = VitessceConfig.from_dict(CFG)
        return vc.widget(height=640, remount_on_uid_change=False)

    heatmap_present = reactive.value(True)
    free_position = reactive.value(False)

    @reactive.effect
    @reactive.event(input.freepos)
    def _():
        free_position.set(input.freepos())

    @render.text
    def view_state():
        cfg = reactive_read(vit.widget, "_config")
        cs = cfg.get("coordinationSpace", {})

        def first(name):
            v = list(cs.get(name, {}).values())
            return v[0] if v else None

        zoom = first("spatialZoom")
        views = [
            f"{v['component']}@({v.get('x')},{v.get('y')},{v.get('w')}x{v.get('h')})"
            for v in cfg.get("layout", [])
        ]
        return (
            f"spatialZoom: {zoom if zoom is None else round(zoom, 2)}\n"
            f"featureSelection: {first('featureSelection')}\n"
            + "\n".join(views)
        )

    # 1. Coordination edit -- same pattern as examples/vitessce.
    @reactive.effect
    @reactive.event(input.gene, ignore_init=True)
    def _():
        new = copy.deepcopy(vit.widget._config)
        new["coordinationSpace"]["featureSelection"]["A"] = [input.gene()]
        bump_and_write(vit.widget, new)

    # 2. Structural change -- remove/re-add a view from the layout.
    @reactive.effect
    @reactive.event(input.toggle)
    def _():
        new = copy.deepcopy(vit.widget._config)
        if heatmap_present():
            new["layout"] = [
                v for v in new["layout"] if v["component"] != "heatmap"
            ]
        else:
            entry = copy.deepcopy(HEATMAP_VIEW)
            # WORKAROUND for a vit-s bug: the in-place adoption path
            # (remountOnUidChange=False) puts the RAW config prop into the
            # store (VitessceGrid's effect uses `config`, not the
            # validated/initialized `configOrWarning`), so assignViewUids
            # never runs and a new view without a uid breaks react-grid-layout
            # (layout item i=undefined, child key=null -> not rendered).
            # Assigning an explicit, unique view uid should fix the render.
            entry["uid"] = "hm-" + str(uuid.uuid4())[:8]
            if free_position():
                # Place below whatever the grid currently occupies, in case
                # RGL compaction moved other views into the original slot.
                bottom = max(v.get("y", 0) + v.get("h", 1) for v in new["layout"])
                entry["x"], entry["y"] = 0, bottom
            new["layout"] = new["layout"] + [entry]
        heatmap_present.set(not heatmap_present())
        bump_and_write(vit.widget, new)

    # 3. Full reset -- write the PRISTINE config (default zoom etc.), so if
    # this resets the viewport, full-reset behavior is still achievable
    # without a remount.
    @reactive.effect
    @reactive.event(input.reset)
    def _():
        bump_and_write(vit.widget, copy.deepcopy(CFG))
        heatmap_present.set(True)


app = App(app_ui, server)
