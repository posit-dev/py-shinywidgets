import ipyvolume as ipv
import numpy as np
from shiny.express import ui

from shinywidgets import render_ipyvolume

ui.page_opts(title="Surface", fillable=True)

u = np.linspace(-5, 5, 60)
x, y = np.meshgrid(u, u)
r = np.sqrt(x**2 + y**2) + 1e-6
z = np.sin(r) / r


@render_ipyvolume
def plot():
    ipv.figure()
    ipv.plot_surface(x, z, y, color="orange")
    ipv.plot_wireframe(x, z, y, color="black")
    return ipv.gcf()
