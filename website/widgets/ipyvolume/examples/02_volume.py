import ipyvolume as ipv
import numpy as np
from shiny.express import ui

from shinywidgets import render_ipyvolume

ui.page_opts(title="Volume rendering", fillable=True)

# A synthetic density field (two overlapping Gaussian blobs) standing in for
# a CT/MRI-style 3D array -- any (nx, ny, nz) numpy array works.
grid = np.linspace(-1, 1, 64)
gx, gy, gz = np.meshgrid(grid, grid, grid, indexing="ij")
blob_a = np.exp(-((gx - 0.25) ** 2 + gy**2 + gz**2) / 0.05)
blob_b = np.exp(-((gx + 0.3) ** 2 + (gy - 0.2) ** 2 + gz**2) / 0.08)
density = blob_a + 0.7 * blob_b


@render_ipyvolume
def plot():
    ipv.quickvolshow(density, level=[0.2, 0.5, 0.8], opacity=[0.01, 0.05, 0.12])
    return ipv.gcf()
