# Any in-memory numpy array can be viewed directly -- no zarr store, no file,
# no server. vizarr wraps the array in a single-chunk in-memory zarr store and
# streams it to the browser over the Shiny websocket. `scipy.datasets.face()`
# downloads a small sample photo the first time it's called (cached after).
import numpy as np
import vizarr
from scipy.datasets import face
from shiny.express import ui

from shinywidgets import render_vizarr

gray = np.mean(face(), axis=-1).astype(np.uint8)  # (768, 1024) grayscale

ui.page_opts(title="vizarr: a plain numpy array", fillable=True)

with ui.card(full_screen=True):

    @render_vizarr
    def viewer():
        v = vizarr.Viewer()
        v.add_image(source=gray, name="raccoon")
        return v
