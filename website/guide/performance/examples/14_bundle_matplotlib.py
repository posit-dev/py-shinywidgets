import matplotlib.pyplot as plt
import numpy as np
from shiny.express import ui
from shinywidgets import render_matplotlib

ui.page_opts(title="bundle: matplotlib", fillable=True)


@render_matplotlib
def plot():
    fig, ax = plt.subplots()
    rng = np.random.default_rng(42)
    ax.scatter(rng.normal(size=50), rng.normal(size=50))
    return fig
