# This will load the ipyshiny module dynamically, without having to install it.
# This makes the debug/run cycle quicker.
from shiny import *
from ipyshiny import *
import numpy as np
import os
import sys

shiny_module_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, shiny_module_dir)


#import ipywidgets as ipy
#input_ipywidget("IntSlider", ipy.IntSlider(value=4))


ui = page_fluid(
    output_ipywidget("ipyvolume")
)


def server(ss: ShinySession):

    @ss.output("ipyvolume")
    @render_ipywidget()
    def _():
        from ipyvolume import quickquiver

        x, y, z, u, v, w = np.random.random((6, 1000)) * 2 - 1
        return quickquiver(x, y, z, u, v, w, size=5)

app = ShinyApp(ui, server)
if __name__ == "__main__":
    app.run()
