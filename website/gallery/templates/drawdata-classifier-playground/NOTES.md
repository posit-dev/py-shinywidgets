# Verification notes

- Source: promoted from
  `docs/widget-guides/drawdata/gallery/template_classifier_playground.py`. Header reformatted to
  the gallery convention; no logic changes.
- Re-verified 2026-11-02 on the `origin/main` worktree: `uv run --no-sync --with scikit-learn shiny
  run app.py`, port 10081. Drew 5 points for class "a" and 5 for class "b" via real mouse
  down/move/up gestures, switching class with the "b" button (`img/after.webp`): "10 points drawn"
  and a correctly-fitted k-NN decision boundary separating the two clusters.
- `--with scikit-learn` is unpinned (not in the locked venv); low risk here (only `KNeighborsClassifier`
  is used, a stable API).
- No new shinywidgets bugs found; see `drawdata/NOTES.md` for upstream drawdata quirks (first-batch
  sync delay, BarWidget trait-write limitations) not exercised by this template.

## Update 2026-11-11 (main @ 32ca7035)

- **Narrative fix**: both call sites of `reactive_read(canvas.widget, "data")` converted to
  `canvas.read("data")` (tier 2, the taught fallback for a renderer output's bare synced traits).
  Dropped the now-unused `reactive_read` import.
- Re-verified with Playwright (`--with scikit-learn`): drew 8 points for class "a" then switched
  to "b" and drew 8 more -- "16 points drawn" and a correctly-fitted k-NN boundary separating the
  two clusters, matching the 2026-11-02 pass's outcome shape (same first-batch-sync-delay quirk:
  16 clicks produced 16 synced points here, consistent with the upstream drawdata behavior
  documented in the `drawdata` guide). No console/server errors beyond the pre-existing,
  unrelated upstream console warning noted below.
- **Pre-existing, not a regression**: the smoke report flagged a console error on this app
  (`Error: <svg> attribute height: Expected length, "auto".`). Reproduced here too, from
  drawdata's own SVG canvas (not from shinywidgets or this template's code); didn't affect
  drawing, class switching, or the point count. Not attributed to the accessor change -- logged
  for completeness, not fixed (upstream drawdata quirk).
- Accessors: `canvas.read("data")` -- verified with a real gesture (drawing both classes), value
  confirmed against both `#status` and the refitted decision boundary.
