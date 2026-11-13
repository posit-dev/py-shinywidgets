import numpy as np
from matplotlib.figure import Figure
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_matplotlib

ui.page_opts(fillable=True)

cities = ["Austin", "Boise", "Chicago", "Denver", "Eugene", "Fargo"]
pop = np.array([980, 235, 2700, 715, 175, 125])
growth = np.array([2.8, 3.1, 0.4, 2.2, 1.6, 0.9])


@render_matplotlib
def plot():
    fig = Figure(layout="constrained")
    ax = fig.subplots()
    ax.scatter(pop, growth, s=80, picker=5)
    ax.set_xlabel("Population (thousands)")
    ax.set_ylabel("Growth rate (%)")
    return fig


@render.code
def picked():
    ev = req(plot.picked())
    i = ev.ind[0]
    return f"{cities[i]}: {pop[i]}k people, {growth[i]}% growth"
