# Uses bokeh's own sample-data package (downloaded on first use):
#   pip install bokeh_sampledata
from bokeh.plotting import figure
from bokeh.sampledata.autompg import autompg as df
from shiny.express import ui
from shinywidgets import render_bokeh

ui.page_opts(title="Bokeh quickstart", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Fuel economy vs. weight (1970-82 cars)")

    @render_bokeh
    def plot():
        p = figure(title="EPA mileage drops as cars get heavier")
        p.xaxis.axis_label = "weight (lbs)"
        p.yaxis.axis_label = "mpg"
        p.scatter(df.weight, df.mpg, size=8, alpha=0.6)
        return p
