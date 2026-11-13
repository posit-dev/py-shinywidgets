import base64
import json

import numpy as np
from shiny.express import render, ui
from shinywidgets import render_widget

from sparkline_widget import BinarySparkline

N = 20_000
rng = np.random.default_rng(3)
DATA = rng.normal(size=N).cumsum().astype("float32")

ui.page_opts(title="anywidget: a binary trait for bigger data", fillable=True)

with ui.card():
    ui.card_header(f"{N:,} points as a packed float32 buffer, not a JSON list")

    @render_widget
    def spark():
        return BinarySparkline(values=DATA.tobytes())

with ui.card():
    ui.card_header(f"Measured payload for this array (same {N:,} floats either way)")

    @render.code
    def sizes():
        as_json = json.dumps(DATA.tolist()).encode()
        as_binary_b64 = base64.b64encode(DATA.tobytes())
        return (
            f"JSON list trait:      {len(as_json):>8,} bytes\n"
            f"Bytes trait (base64): {len(as_binary_b64):>8,} bytes "
            f"(raw buffer: {DATA.nbytes:,} bytes)"
        )
