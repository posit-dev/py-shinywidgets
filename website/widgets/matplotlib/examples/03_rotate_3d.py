import numpy as np
from matplotlib.cbook import get_sample_data
from matplotlib.figure import Figure
from shiny.express import ui
from shinywidgets import render_matplotlib

ui.page_opts(fillable=True)

# A real elevation survey, bundled with matplotlib as sample data
dem = get_sample_data("jacksboro_fault_dem.npz")
z = dem["elevation"][::4, ::4]
x = np.linspace(dem["xmin"], dem["xmax"], z.shape[1])
y = np.linspace(dem["ymin"], dem["ymax"], z.shape[0])
X, Y = np.meshgrid(x, y)


@render_matplotlib
def plot():
    fig = Figure(layout="constrained")
    ax = fig.add_subplot(projection="3d")
    ax.plot_surface(X, Y, z, cmap="terrain")
    ax.set_zlabel("Elevation (ft)")
    return fig
