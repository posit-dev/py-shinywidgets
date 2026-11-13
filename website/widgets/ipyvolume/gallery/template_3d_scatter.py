# Title: 3D scatter starting point
# A clean, adaptable template: direct Figure/Scatter construction, explicit
# axis limits, an in-place restyle slider, and the camera() accessor read out
# as live text. Bucket: template (~70 lines).
# Run: uv run shiny run gallery/template_3d_scatter.py
# Data: plotly.express.data.iris() (bundled with plotly)
import ipyvolume as ipv
import numpy as np
import plotly.express as px
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import render_ipyvolume

ui.page_opts(title="3D scatter template", fillable=True)

iris = px.data.iris()
palette = np.array([[0.91, 0.30, 0.24], [0.18, 0.49, 0.20], [0.21, 0.45, 0.69]])
color = palette[iris["species_id"] - 1]

with ui.sidebar():
    ui.input_slider("size", "Point size", 0.3, 3, 1.2, step=0.1)
    ui.markdown("Drag to orbit, scroll to zoom.")

    @render.text
    def camera_readout():
        cam = plot.camera()
        return f"camera: ({cam.position[0]:.2f}, {cam.position[1]:.2f}, {cam.position[2]:.2f})"

with ui.card(full_screen=True):
    ui.card_header("sepal length / petal length / sepal width, by species")

    @render_ipyvolume
    def plot():
        # Direct construction: set axis limits explicitly (no auto-fit) and
        # keep the figure cheap to re-render (data rarely changes here).
        fig = ipv.figure()
        ipv.scatter(
            iris["sepal_length"], iris["petal_length"], iris["sepal_width"],
            size=1.2, marker="sphere", color=color,
        )
        fig.xlim = [iris["sepal_length"].min(), iris["sepal_length"].max()]
        fig.ylim = [iris["petal_length"].min(), iris["petal_length"].max()]
        fig.zlim = [iris["sepal_width"].min(), iris["sepal_width"].max()]
        return fig


# In-place update: resize the existing points instead of re-rendering.
@reactive.effect
def _resize():
    plot.widget.scatters[0].size = input.size()
