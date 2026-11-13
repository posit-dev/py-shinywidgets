# NOTES: single-cell-atlas

- Promoted from `docs/widget-guides/jscatter/gallery/showcase_single_cell_atlas.py`. The
  original used the `__doc__ = """..."""` assignment trick; **converted to a plain
  `#`-comment header** for consistency with this bucket's convention (see
  `les-miserables-network/NOTES.md` for the same judgment call and rationale).
- Re-verified 2026-11-02 in `main-wt`: `jupyter-scatter` 1.0.1, already in the shared venv's
  `test` dependency group (package name `jupyter-scatter`, import name `jscatter` -- easy to
  miss when grepping `uv pip list` for "jscatter"). No `--with` overlay needed.

## Verification table

| Gesture | Driven | Server-state confirmed |
|---|---|---|
| Load + both scatter plots render | yes (Playwright, swiftshader WebGL flags) | both `#umap canvas` and `#genes canvas` visible, `img/hero.webp` |
| Click "Find the top 1% CD3E cells" | yes | `#n_selected` changed from `"All 300,000 cells"` to `"3,000 cells selected (1.0%)"`, embedding visibly zoomed and recolored its composition breakdown, `img/after_top.webp` |

Did not separately re-drive the raw lasso-drag gesture or the "Clear selection" button in
this pass; the button-driven selection above exercises the same `selected()` accessor and
the two-way mirroring effect (`umap` -> `genes`), which is the showcase's core mechanism.

## Judgment calls

- Converted the `__doc__` trick to a `#`-comment header (same call as
  `les-miserables-network`).
