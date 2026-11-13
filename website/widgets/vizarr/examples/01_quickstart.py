# A public OME-NGFF (OME-Zarr) sample from the Image Data Resource (IDR): a
# spinning-disk confocal z-stack of nuclei (LaminB1 in blue, DAPI in yellow).
# vizarr's browser code fetches this URL directly -- shinywidgets never sees
# the pixel data.
import vizarr
from shiny.express import ui

from shinywidgets import render_vizarr

IDR_SAMPLE = "https://minio-dev.openmicroscopy.org/idr/v0.3/idr0062-blin-nuclearsegmentation/6001240.zarr"

ui.page_opts(title="vizarr quick start", fillable=True)

with ui.card(full_screen=True):

    @render_vizarr
    def viewer():
        v = vizarr.Viewer()
        v.add_image(source=IDR_SAMPLE)
        return v
