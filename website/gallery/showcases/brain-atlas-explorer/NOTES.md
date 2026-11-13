# NOTES: brain-atlas-explorer

- Promoted from `docs/widget-guides/niivue/gallery/showcase_atlas_explorer.py`, unchanged
  except the `# Run:` header line (drops the redundant `--with ipyniivue`, since ipyniivue is
  already in the shared worktree's base venv; keeps `--with nibabel`, which genuinely isn't).
- Re-verified 2026-11-02 in `main-wt`: ipyniivue 2.4.4, nibabel installed fresh via
  `--with nibabel`. The MNI152 template was already cached at `~/.cache/niivue-guide/` from
  the niivue guide's own earlier run; confirmed both `niivue.com/demos/images/aal.json` and
  `aal.nii.gz` were reachable from this machine at verification time (HTTP 200 on both).

## Bugs found

- None new. Confirms the niivue guide's finding: setting `scene.crosshair_pos` from Python
  moves the crosshair but never fires `location()` -- the showcase's landmark dropdown and
  click-to-identify card rely on exactly this split (see Gotchas in the README).

## Update 2026-11-11 (main @ 32ca7035)

- **Bug fixed** (regression from the accessor redesign, not present at the 2026-11-02
  verification above): `location()` moved to the new eager "state" accessor pattern (#437) and
  now seeds itself at render from the viewer's current crosshair (see `shinywidgets/_niivue.py`).
  That seed payload is `{"frac": [...], "seeded": True}` -- no `"values"`/`"mm"` keys -- so
  `region_card()`'s old `if loc is None` guard no longer caught the no-interaction-yet case, and
  `loc["values"][1]["value"]` raised `KeyError: 'values'` on first render (this is exactly what
  the shared smoke report flagged: `gallery/showcases/brain-atlas-explorer/app.py` ->
  `region_card: 'values'`). Fixed per the brief's guidance to check the `"seeded"` key instead of
  `is None`.
- Verified with Playwright (`--with nibabel`, swiftshader WebGL flags): initial render shows the
  placeholder text with no server error (previously a `KeyError` on every load); a real canvas
  click lands on "Insula L" at MNI (-47, -5, -0) with the region card populated correctly.
  Replaced `img/after_click.webp` with this run's screenshot. Server log had zero tracebacks
  across both states.
- Accessors: `brain.location()` -- verified with a real gesture (click), both the seeded and
  post-click states screenshotted and read. The landmark-dropdown asymmetry documented in the
  README (Python-set `crosshair_pos` doesn't fire `location()`) still holds; not re-verified this
  pass since the code path is unchanged.

## Verification table

| Gesture | Driven | Server-state confirmed |
|---|---|---|
| Load + viewer renders | yes (Playwright, swiftshader WebGL flags) | `#brain canvas` visible, `img/hero.webp` |
| Select "Primary visual cortex" from the landmark dropdown | yes | crosshair visibly moved to a posterior slice in `img/after_landmark.webp`; `#region_card` correctly unchanged (no click occurred) |
| Real click on the canvas | yes | `#region_card` changed from the placeholder to `"Occipital Sup L", MNI (-14, -88, 10) mm`, `img/after_click.webp` |

## Judgment calls

- Added a second gesture (a real canvas click, beyond what the promoted app's own
  `after_landmark` screenshot shows) specifically to verify `location()` itself, since the
  landmark-jump screenshot alone could be mistaken for a `location()` firing when it isn't.
  Recommend the website's copy for this showcase keep both screenshots, captioned to make
  the distinction explicit.
