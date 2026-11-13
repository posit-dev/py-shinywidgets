import ipyvolume as ipv
import numpy as np
from shiny.express import ui

from shinywidgets import render_ipyvolume

ui.page_opts(title="Quiver", fillable=True)

# A synthetic vortex vector field: points on a grid, with (u, v, w) giving
# the arrow direction at each point.
lin = np.linspace(-2, 2, 6)
x, y, z = np.meshgrid(lin, lin, lin, indexing="ij")
x, y, z = x.ravel(), y.ravel(), z.ravel()
u, v, w = -y, x, np.zeros_like(z) + 0.3


@render_ipyvolume
def plot():
    ipv.figure()
    ipv.quiver(x, y, z, u, v, w, size=8, color="steelblue")
    return ipv.gcf()
