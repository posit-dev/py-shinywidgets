# This will load the ipyshiny module dynamically, without having to install it.
# This makes the debug/run cycle quicker.
import os
import sys

shiny_module_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, shiny_module_dir)

import ipywidgets as ipy
from shiny import *
from ipyshiny import *

ui = page_fluid(
    input_ipywidget(
      "IntSlider", 
      ipy.IntSlider(value=4, min=1, max=20)
    ),
    input_ipywidget(
      "DatePicker",
      ipy.DatePicker()
    ),
    input_ipywidget(
      "SelectMultiple",
      ipy.SelectMultiple(
          options=['Apples', 'Oranges', 'Pears'],
          value=['Oranges'],
          #rows=10,
          description='Fruits',
          disabled=False
      )
    ),
    input_ipywidget(
        "RadioButtons",
        ipy.RadioButtons(
            options=[('pepperoni', 'pep'), ('pineapple', 'pine'),
                     ('anchovies', 'anch')],
            value='pine',
            description='Pizza topping:',
            disabled=False
        )
    ),
    #output_ipywidget("ipyleaflet")
    output_ui("slider"),
    output_ui("picker"),
    output_ui("select"),
    output_ui("radio"),
)

def server(ss: ShinySession):
    #@ss.output("ipyleaflet")
    #@render_ui()
    #def _():
    #    from ipyleaflet import Map, Marker
#
    #    zoom = ss.input["IntSlider"]
    #    zoom = zoom if zoom is not None else 4
    #    m = Map(center=(52.204793, 360.121558), zoom=zoom)
    #    m.add_layer(Marker(location=(52.204793, 360.121558)))
    #    return m

    @ss.output("slider")
    @render_ui()
    def _():
      return ss.input["IntSlider"] 

    @ss.output("picker")
    @render_ui()
    def _():
        return ss.input["DatePicker"]

    @ss.output("select")
    @render_ui()
    def _():
        return ss.input["SelectMultiple"]

    @ss.output("radio")
    @render_ui()
    def _():
        return ss.input["RadioButtons"]

app = ShinyApp(ui, server)
if __name__ == "__main__":
    app.run()
