from typing import List, Optional, Tuple

import ipyleaflet as leaf
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.figure_factory as ff
import plotly.graph_objs as go
import shiny
from ipyleaflet import basemaps


def create_map(**kwargs):
    map = leaf.Map(
        center=(37.45, -88.85),
        zoom=4,
        scroll_wheel_zoom=True,
        attribution_control=False,
        **kwargs,
    )
    map.add_layer(leaf.basemap_to_tiles(basemaps.CartoDB.DarkMatter))
    search = leaf.SearchControl(
        url="https://nominatim.openstreetmap.org/search?format=json&q={s}",
        position="topleft",
        zoom=10,
    )
    map.add(search)
    return map

def density_plot(
    overall: pd.DataFrame,
    in_bounds: pd.DataFrame,
    var: str,
    selected: Optional[pd.DataFrame] = None,
    title: Optional[str] = None,
    showlegend: bool = False,
):
    shiny.req(not in_bounds.empty)

    dat = [overall[var], in_bounds[var]]
    if var == "Population":
        dat = [np.log10(x) for x in dat]

    # Create distplot with curve_type set to 'normal'
    fig = ff.create_distplot(
        dat,
        ["Overall", "In bounds"],
        colors=["black", "#6DCD59"],
        show_rug=False,
        show_hist=False,
    )
    # Remove tick labels
    fig.update_layout(
        # hovermode="x",
        height=200,
        showlegend=showlegend,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(x=0.5, y=1, orientation="h", xanchor="center", yanchor="bottom"),
        xaxis=dict(
            title=title if title is not None else var,
            showline=False,
            zeroline=False,
        ),
        yaxis=dict(
            showgrid=False,
            showline=False,
            showticklabels=False,
            zeroline=False,
        ),
        template="plotly_white"
    )
    # hovermode itsn't working properly when dynamically, absolutely positioned
    for _, trace in enumerate(fig.data):
        trace.update(hoverinfo="none")

    if selected is not None:
        x = selected[var].tolist()[0]
        if var == "Population":
            x = np.log10(x)
        fig.add_shape(
            type="line",
            x0=x,
            x1=x,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(width=1, dash="dashdot", color="gray"),
        )

    return go.FigureWidget(data=fig.data, layout=fig.layout)


color_palette = plt.get_cmap("viridis", 10)

# TODO: how to handle nas (pd.isna)?
def col_numeric(domain: Tuple[float, float], na_color: str = "#808080"):
    rescale = mpl.colors.Normalize(domain[0], domain[1])

    def _(vals: List[float]) -> List[str]:
        cols = color_palette(rescale(vals))
        return [mpl.colors.to_hex(v) for v in cols]

    return _


# R> cat(paste0(round(scales::rescale(log10(1:10), to = c(0.05, 1)), 2), ": '", viridis::viridis(10), "'"), sep = "\n")
heatmap_gradient = {
    0.05: "#440154",
    0.34: "#482878",
    0.5: "#3E4A89",
    0.62: "#31688E",
    0.71: "#26828E",
    0.79: "#1F9E89",
    0.85: "#35B779",
    0.91: "#6DCD59",
    0.96: "#B4DE2C",
    1: "#FDE725",
}
