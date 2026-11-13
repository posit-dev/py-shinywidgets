import os

import numpy as np
import pandas as pd
from shiny.express import ui
from shinywidgets import render_perspective

N = int(os.environ.get("PERF_N", "10000"))
rng = np.random.default_rng(42)
df = pd.DataFrame({"x": rng.normal(size=N), "y": rng.normal(size=N)})

ui.page_opts(title=f"perspective: {N:,} rows", fillable=True)


@render_perspective
def grid():
    return df
