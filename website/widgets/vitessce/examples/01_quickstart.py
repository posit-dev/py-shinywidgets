# Vitessce quick start: one remote AnnData-Zarr store, a spatial view, and
# its cell-sets legend. Requires an internet connection (zarr data + viewer
# JS are remote).
from shiny.express import ui
from vitessce import ViewType as vt, VitessceConfig

from shinywidgets import render_vitessce

ui.page_opts(title="Vitessce quick start", fillable=True)

DATA_URL = (
    "https://data-1.vitessce.io/0.0.33/main/human-lymph-node-10x-visium/"
    "human_lymph_node_10x_visium.h5ad.zarr"
)


@render_vitessce
def vit():
    vc = VitessceConfig(schema_version="1.0.15", name="Human lymph node (10x Visium)")
    dataset = vc.add_dataset(name="Lymph node").add_file(
        url=DATA_URL,
        file_type="anndata.zarr",
        # Tell Vitessce which zarr arrays hold spot coordinates, spot shapes,
        # and cluster labels (the latter is also what colors the spots by
        # default). Visium spots render from obsSegmentations, not just
        # obsLocations -- without it, the view mounts but draws nothing.
        options={
            "obsLocations": {"path": "obsm/spatial"},
            "obsSegmentations": {"path": "obsm/segmentations"},
            "obsSets": [{"name": "Leiden Cluster", "path": "obs/clusters"}],
        },
    )
    spatial = vc.add_view(vt.SPATIAL, dataset=dataset)
    sets = vc.add_view(vt.OBS_SETS, dataset=dataset)
    vc.layout(spatial | sets)
    return vc
