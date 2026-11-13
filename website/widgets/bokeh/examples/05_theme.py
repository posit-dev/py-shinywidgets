import numpy as np
from bokeh.document import Document
from bokeh.plotting import figure
from bokeh.themes import built_in_themes
from shiny.express import ui
from shinywidgets import render_bokeh

ui.page_opts(title="A themed plot", fillable=True)

rng = np.random.default_rng(2)

with ui.card(full_screen=True):

    @render_bokeh
    def plot():
        doc = Document(theme=built_in_themes["night_sky"])
        p = figure(title="night_sky theme", sizing_mode="stretch_both")
        p.scatter(rng.normal(size=150), rng.normal(size=150), size=8, alpha=0.8)
        doc.add_root(p)
        return p
