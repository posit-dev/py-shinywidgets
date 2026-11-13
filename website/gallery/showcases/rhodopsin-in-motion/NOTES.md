# NOTES: rhodopsin-in-motion

- Promoted from `docs/widget-guides/nglview/gallery/showcase_md_explorer.py`, unchanged
  except the `# Run:` header line (now `app.py` relative to this directory).
- Re-verified 2026-11-02 in `main-wt`: nglview 4.0.1, mdtraj installed fresh via
  `--with mdtraj` (not a locked dependency of the project; the nglview guide's own NOTES.md
  made the same observation -- "nothing else depends on a specific mdtraj version", so an
  unpinned overlay carries none of the version-drift risk the brief warns about for
  already-locked packages).

## Verification table

| Gesture | Driven | Server-state confirmed |
|---|---|---|
| Load + structure/chart render | yes (Playwright, swiftshader WebGL flags) | `#structure canvas` visible, `img/hero.webp` |
| Click a point on the RMSD chart | yes (real click on a plotly marker path) | `#frame` slider value changes `0` -> `20`, `img/after_click.webp` shows the moved dashed reference line and a visibly different structure pose |

Did not separately re-drive the atom-click -> `picked` trait path or the
representation/residue-highlight controls in this pass; the nglview guide's own
verification already covers those, and the frame-linking gesture above is the one most
central to this showcase's premise (one shared value driving three views).

## Judgment calls

- None beyond the header-line edit.

## Update 2026-11-11 (main @ 32ca7035)

- **Narrative fix**: `atom_info()` used `reactive_read(structure.widget, "picked")`. Converted
  to `structure.read("picked")` (tier 2 -- `.read()` is now the taught fallback for a renderer
  output's bare synced traits); dropped the `reactive_read` import, no longer used.
- Verified with Playwright (`--with mdtraj`, swiftshader WebGL flags), filling the gap the
  2026-11-02 pass explicitly left open: a real click on the 3D structure (not just the RMSD
  chart) populated **Picked atom** with `"TRP 265 chain B"`, added `img/after_atom_click.webp`
  showing the picked-atom tooltip and sidebar in sync (kept the existing `img/after_click.webp`,
  which documents the chart-click gesture). No console/server errors.
- Accessors: `rmsd_plot.clicked()` -- not re-driven this pass (already verified 2026-11-02, code
  path unchanged). `structure.read("picked")` -- verified with a real gesture this pass.
