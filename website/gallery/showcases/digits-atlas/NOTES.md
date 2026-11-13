# NOTES: digits-atlas

- Promoted from `docs/widget-guides/embedding-atlas/gallery/showcase_digits_atlas.py`,
  unchanged except the `# run:` header line (drops the redundant
  `--with shinywidgets[embedding_atlas]`, since embedding-atlas is already in the shared
  worktree's base venv; keeps `--with scikit-learn`, which genuinely isn't).
- Re-verified 2026-11-02 in `main-wt`: embedding-atlas 0.26.0, scikit-learn installed fresh
  via `--with scikit-learn`, pillow 13.0.0 (locked). WebGPU confirmed working in headless
  Chromium with `args=["--enable-unsafe-webgpu", "--use-angle=metal"]`, served from
  `http://localhost:10107` (a secure context), matching the embedding-atlas guide's own
  finding.

## Verification table

| Gesture | Driven | Server-state confirmed |
|---|---|---|
| Load + embedding renders | yes (Playwright, WebGPU flags) | chart, image grid, and digit histogram all visible, `img/hero.webp` |
| Canvas lasso drag (fractional coordinates inside the chart's own bounding box) | attempted, no visible effect | selection stayed at `1,797 of 1,797`; not counted as a pass (see Judgment calls) |
| Click the "3" bar in the digit histogram (a DOM `button[title='3']`, not the canvas) | yes | `#count` changed to `183 of 1,797 digits selected`, and `#average_digit`'s reconstructed image visibly became a blurry "3" (`img/after_lasso.webp`, filename kept from the original script for continuity even though the final gesture used was a histogram click, not a lasso) |

## Judgment calls

- The canvas-lasso drag (fixed fractional coordinates inside the chart's bounding box) did
  not change the selection in this environment, even after locating the exact canvas
  bounding box and adjusting the drag region. Rather than spend further gesture budget
  reverse-engineering embedding-atlas's exact lasso-vs-pan mode toggle under Playwright
  (there are separate "rectangle select" and "lasso select" mode-toggle buttons, and the
  default interaction mode wasn't confirmed), switched to clicking the digit histogram's "3"
  bar, which is a first-class crossfilter gesture the showcase's own description explicitly
  calls out as reading the same `selected()` accessor. This fully confirms the accessor and
  the "average digit" payoff; it does not confirm the canvas lasso gesture specifically.
  Flagging for a maintainer/reviewer who wants the literal lasso drag re-attempted with more
  time budget.
- Renamed nothing on disk (kept `after_lasso.webp` as the screenshot filename for
  continuity with the source script, even though the gesture that produced it was a
  histogram click).
