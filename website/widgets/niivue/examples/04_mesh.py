# A cortical surface mesh with a functional-activity layer draped on top --
# meshes render alongside (or instead of) volumes.
from ipyniivue import Mesh, MeshLayer, NiiVue
from shiny.express import ui
from shinywidgets import render_niivue

ui.page_opts(title="Cortical surface mesh", fillable=True)


@render_niivue
def brain():
    nv = NiiVue()
    nv.load_meshes(
        [
            Mesh(
                url="https://niivue.com/demos/images/BrainMesh_ICBM152.lh.mz3",
                rgba255=[200, 200, 200, 255],
                layers=[
                    MeshLayer(
                        url="https://niivue.com/demos/images/BrainMesh_ICBM152.lh.motor.mz3",
                        colormap="warm",
                        opacity=0.7,
                    )
                ],
            )
        ]
    )
    return nv
