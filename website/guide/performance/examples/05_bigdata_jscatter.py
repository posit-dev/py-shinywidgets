import os

import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny.express import ui
from shinywidgets import render_jscatter

N = int(os.environ.get("PERF_N", "10000"))
rng = np.random.default_rng(42)
df = pd.DataFrame({"x": rng.normal(size=N), "y": rng.normal(size=N)})

ui.page_opts(title=f"jscatter: {N:,} points", fillable=True)


@render_jscatter
def plot():
    return Scatter(data=df, x="x", y="y")
