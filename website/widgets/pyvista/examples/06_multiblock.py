import pyvista as pv
from shiny.express import ui
from shinywidgets import render_pyvista

pv.OFF_SCREEN = True

ui.page_opts(fillable=True)

# A MultiBlock keeps each part addressable by name -- useful for assemblies
# (mechanical parts, anatomical structures, ...) where each piece needs its
# own color, opacity, or visibility
assembly = pv.MultiBlock(
    {
        "base": pv.Cylinder(center=(0, 0, -0.6), direction=(0, 0, 1), radius=1.2, height=0.4),
        "column": pv.Cylinder(center=(0, 0, 0.3), direction=(0, 0, 1), radius=0.3, height=1.8),
        "head": pv.Sphere(center=(0, 0, 1.5), radius=0.6),
    }
)
colors = {"base": "tab:blue", "column": "tab:gray", "head": "tab:orange"}


@render_pyvista
def plot():
    pl = pv.Plotter()
    for name in assembly.keys():
        pl.add_mesh(assembly[name], color=colors[name], smooth_shading=True)
    pl.view_isometric()
    return pl
