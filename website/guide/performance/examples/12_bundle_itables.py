import pandas as pd
from shiny.express import ui
from shinywidgets import render_itables

df = pd.DataFrame({"x": range(20), "y": range(20)})

ui.page_opts(title="bundle: itables", fillable=True)


@render_itables
def tbl():
    return df
