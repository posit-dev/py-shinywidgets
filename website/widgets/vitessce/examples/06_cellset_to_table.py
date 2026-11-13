# Read interaction state back into Python: check/uncheck cell sets in the
# "Cell Sets" legend and the selection shows up as a table. Requires an
# internet connection.
import pandas as pd
from shiny.express import render, ui
from vitessce import ViewType as vt, VitessceConfig

from shinywidgets import reactive_read, render_vitessce

ui.page_opts(title="Vitessce: selection to table", fillable=True)

DATA_URL = (
    "https://data-1.vitessce.io/0.0.33/main/human-lymph-node-10x-visium/"
    "human_lymph_node_10x_visium.h5ad.zarr"
)
FILE_OPTIONS = {
    "obsFeatureMatrix": {"path": "obsm/X_hvg", "featureFilterPath": "var/highly_variable"},
    "obsLocations": {"path": "obsm/spatial"},
    "obsEmbedding": [{"path": "obsm/X_umap", "embeddingType": "UMAP"}],
    "obsSets": [{"name": "Leiden Cluster", "path": "obs/clusters"}],
}

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_vitessce
        def vit():
            vc = VitessceConfig(schema_version="1.0.15", name="Lymph node")
            dataset = vc.add_dataset(name="Lymph node").add_file(
                url=DATA_URL, file_type="anndata.zarr", options=FILE_OPTIONS
            )
            spatial = vc.add_view(vt.SPATIAL, dataset=dataset)
            umap = vc.add_view(vt.SCATTERPLOT, dataset=dataset, mapping="UMAP")
            sets = vc.add_view(vt.OBS_SETS, dataset=dataset)
            vc.layout((spatial | umap) / sets)
            return vc

    with ui.card():
        ui.card_header("Selected cell sets")

        @render.data_frame
        def selection_table():
            cs = reactive_read(vit.widget, "_config").get("coordinationSpace", {})
            # obsSetSelection is a dict of scope -> list of [group, set-name]
            # paths; every path shares one list in this config (scope "A").
            paths = next(iter(cs.get("obsSetSelection", {}).values()), None) or []
            return pd.DataFrame(paths, columns=["Group", "Set"])
