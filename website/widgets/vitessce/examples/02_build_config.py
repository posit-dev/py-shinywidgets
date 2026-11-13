# Build a config from the Vitessce Python API: one dataset, two linked views.
# Requires an internet connection (zarr data + viewer JS are remote).
from shiny.express import ui
from vitessce import ViewType as vt, VitessceConfig

from shinywidgets import render_vitessce

ui.page_opts(title="Vitessce: build a linked config", fillable=True)

DATA_URL = (
    "https://data-1.vitessce.io/0.0.33/main/human-lymph-node-10x-visium/"
    "human_lymph_node_10x_visium.h5ad.zarr"
)
# The file's internal zarr layout (which obs/var arrays hold what).
FILE_OPTIONS = {
    "obsFeatureMatrix": {"path": "obsm/X_hvg", "featureFilterPath": "var/highly_variable"},
    "obsLocations": {"path": "obsm/spatial"},
    "obsEmbedding": [{"path": "obsm/X_umap", "embeddingType": "UMAP"}],
    "obsSets": [{"name": "Leiden Cluster", "path": "obs/clusters"}],
}


@render_vitessce
def vit():
    vc = VitessceConfig(schema_version="1.0.15", name="Lymph node: spatial + UMAP, linked")
    dataset = vc.add_dataset(name="Lymph node").add_file(
        url=DATA_URL, file_type="anndata.zarr", options=FILE_OPTIONS
    )
    spatial = vc.add_view(vt.SPATIAL, dataset=dataset)
    umap = vc.add_view(vt.SCATTERPLOT, dataset=dataset, mapping="UMAP")
    sets = vc.add_view(vt.OBS_SETS, dataset=dataset)
    # Both views draw from one obsSets coordination scope by default: clicking
    # a cluster in the legend highlights the same cells in the spatial view
    # *and* the UMAP view. That's Vitessce's own coordination -- no Shiny
    # code involved (see "Vitessce's own coordination" below). link_views()
    # (not used here) would let you tie additional types, e.g. ct.SPATIAL_ZOOM,
    # across views that don't share one (e.g. the matching ct.SPATIAL_ZOOM
    # coordination type) by default.
    vc.layout((spatial | umap) / sets)
    return vc
