# Assigning to __doc__ (rather than a bare string literal) keeps this header
# out of the rendered page: shiny.express displays every top-level expression
# statement's value, docstrings included.
__doc__ = """
300,000 cells: lasso to explore (showcase)

A synthetic single-cell "atlas" explorer: two linked jupyter-scatter plots
(a 2D embedding and two marker genes), 300,000 points each. Drag to lasso
(hold Cmd/Meta to add, Alt to remove, scroll to zoom); the other plot and the
composition panel follow. "Color by" restyles both plots in place -- the
300k points cross the wire once, at first render. The two preset buttons
drive the selection and camera from Python.

Run: shiny run showcase_single_cell_atlas.py
Data: synthetic (generated below); no download needed.
"""

import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny import reactive, render
from shiny.express import input, ui
from shinywidgets import render_jscatter

rng = np.random.default_rng(42)
N = 300_000
# cell type: (% of cells, color)
CELL_TYPES = {
    "T cell": (22, "#4cc9f0"), "B cell": (14, "#f72585"), "NK": (8, "#b5179e"),
    "Monocyte": (18, "#ffb703"), "DC": (4, "#fb8500"), "Platelet": (3, "#90be6d"),
    "Erythroid": (6, "#e63946"), "Stem": (2, "#ced4da"), "Neutrophil": (19, "#43aa8b"),
    "Mast": (4, "#9d4edd"),
}  # fmt: skip
TYPES = list(CELL_TYPES)
SHARES, COLORS = zip(*CELL_TYPES.values())
k = rng.choice(len(TYPES), N, p=np.array(SHARES) / 100)
t = rng.uniform(-1, 1, N)
angle, radius = k * 2 * np.pi / len(TYPES), 6 + (k % 3) * 2.5
cells = pd.DataFrame(
    {
        "umap_1": radius * np.cos(angle) + 2.2 * t * np.cos(angle + 1.6) + rng.normal(0, 0.45, N),
        "umap_2": radius * np.sin(angle) + 2.2 * t * np.sin(angle + 1.6) + 2 * t**2 + rng.normal(0, 0.45, N),
        "cell_type": pd.Categorical(np.array(TYPES)[k], categories=TYPES),
        "pseudotime": ((t + 1) / 2).round(3),
    }
)  # fmt: skip
mu = rng.uniform(0.3, 3.2, (len(TYPES), 2))
cells["CD3E"] = np.clip(mu[k, 0] + 0.5 * t + rng.normal(0, 0.3, N), 0, None)
cells["CD14"] = np.clip(mu[k, 1] - 0.4 * t + rng.normal(0, 0.3, N), 0, None)

ALL = np.arange(N, dtype="uint32")
COLOR_MAPS = {"cell_type": dict(zip(TYPES, COLORS)), "CD3E": "plasma", "CD14": "viridis", "pseudotime": "cool"}


def scatter(x, y, labels):
    return (
        Scatter(data=cells, x=x, y=y, color_by="cell_type", color_map=COLOR_MAPS["cell_type"])
        .size(default=1.5)
        .background("#0d1117")
        .axes(labels=labels)
        .legend(True, position="top-right", size="small")
        .tooltip(True, properties=["cell_type", "CD3E", "CD14", "pseudotime"])
        .mouse(mode="lasso")  # drag selects; the toolbar switches back to pan & zoom
        # jscatter always shows the full y-range, so a plot taller than it is
        # wide crops the x-range; start a little zoomed out to compensate
        .camera(distance=1.2)
    )


ui.page_opts(title="300,000 cells: lasso to explore", fillable=True)
with ui.sidebar(width=280):
    ui.input_select("color_by", "Color by", list(COLOR_MAPS))
    ui.input_action_button("top", "Find the top 1% CD3E cells", class_="btn-primary mb-2")
    ui.input_action_button("clear", "Clear selection")
    ui.markdown("_Drag to lasso, hold **Cmd** to add, **Alt** to remove, scroll to zoom._")

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Embedding (UMAP)")

        @render_jscatter
        def umap():
            return scatter("umap_1", "umap_2", ["UMAP 1", "UMAP 2"])

    with ui.layout_columns(col_widths=12, row_heights=[3, 2]):
        with ui.card(full_screen=True):
            ui.card_header("Marker genes")

            @render_jscatter
            def genes():
                return scatter("CD3E", "CD14", ["CD3E (log)", "CD14 (log)"])

        with ui.card():

            @render.text
            def n_selected():
                sel = umap.selected()
                return f"All {N:,} cells" if not len(sel) else f"{len(sel):,} cells selected ({len(sel) / N:.1%})"

            @render.ui
            def composition():
                sel = umap.selected()
                df = cells if not len(sel) else cells.iloc[sel]
                shares = df.cell_type.value_counts(normalize=True).reindex(TYPES)
                rows = [
                    ui.div(
                        ui.span(name, style="display:inline-block;width:6.5em"),
                        ui.span(
                            style=f"display:inline-block;height:.75em;width:{share * 60:.1f}%;"
                            f"background:{color};border-radius:2px"
                        ),
                        ui.span(f" {share:.0%}", class_="text-muted"),
                        class_="small lh-sm",
                    )
                    for name, color, share in zip(TYPES, COLORS, shares)
                    if share >= 0.005
                ]
                return ui.TagList(
                    *rows,
                    ui.p(
                        f"median CD3E {df.CD3E.median():.2f}, CD14 {df.CD14.median():.2f}",
                        class_="small text-muted mt-2 mb-0",
                    ),
                )


# Linked brushing: mirror each plot's selection onto the other one
def link(source, target):
    @reactive.effect
    def _():
        sel = source.selected()
        with reactive.isolate():
            if not np.array_equal(sel, target.widget.selection):
                target.widget.selection = sel


link(umap, genes)
link(genes, umap)


# Restyle both plots in place; isolate() keeps this from re-rendering them
@reactive.effect
def _recolor():
    by = input.color_by()
    with reactive.isolate():
        for plot in (umap, genes):
            plot.value.color(by=by, map=COLOR_MAPS[by])


# Python drives the selection and camera too
@reactive.effect
@reactive.event(input.top)
def _select_top():
    top = np.flatnonzero(cells.CD3E >= cells.CD3E.quantile(0.99)).astype("uint32")
    with reactive.isolate():
        umap.widget.selection = top
        umap.value.zoom(to=top, animation=800, padding=0.6)


@reactive.effect
@reactive.event(input.clear)
def _clear():
    with reactive.isolate():
        umap.widget.selection = np.array([], dtype="uint32")
        umap.value.zoom(to=ALL, animation=800, padding=0.1)
