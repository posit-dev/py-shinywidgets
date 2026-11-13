# NOTES: chemical-explorer

- Promoted from `docs/widget-guides/mols2grid/gallery/showcase_chem_explorer.py`, unchanged
  except the `# Run:` header line.
- Re-verified 2026-11-02 in `main-wt`: mols2grid 2.2.0, rdkit 2026.9.1, plotly (locked
  version), no `--with` overlay needed -- everything the app imports is already in the
  shared venv.
- Expected RDKit SMILES parse warnings appear in the server log at startup (invalid SMILES
  in the bundled dataset are dropped via `dropna`); this matches the mols2grid guide's own
  findings and is not a regression.

## Verification table

| Gesture | Driven | Server-state confirmed |
|---|---|---|
| Load + grid/scatter render | yes (Playwright) | grid and scatter both visible, `img/hero.webp` |
| Click a molecule's `.m2g-callback` cell | yes (real click, using the same selector the mols2grid Playwright test suite uses for `clicked()`) | "Click a molecule" card goes from "Click a molecule's image to inspect it." to a rendered depiction + `MW 86.2 LogP 2.44 LogS -3.68`, `img/after_click.webp` |

Did not re-drive the slider filters or the plotly lasso -> grid filter in this pass (the
mols2grid guide's own verification already gesture-confirmed both); this promotion's gesture
budget went to `clicked()`, the accessor most central to the showcase's "wow" moment.

## Judgment calls

- None beyond the header-line edit.
