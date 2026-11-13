# NOTES: world-development-dashboard

- Promoted from `docs/widget-guides/lonboard/gallery/showcase_world_dashboard.py` (unchanged
  except the `# Run:` header line, repointed at the showcase's own `app.py`). The lonboard
  guide's own verification (`lonboard/NOTES.md`) already gesture-verified this exact app with
  before/after/detail/restyle screenshots.
- Re-verified in this pass, 2026-11-02: `shinywidgets` @ `origin/main-wt` detached worktree,
  shiny 1.9.0, lonboard 0.17.0, geopandas 1.2.0. Ran via
  `uv run --no-sync python -m shiny run --port 10100 app.py` from the shared worktree.
- Both Natural Earth GeoJSON URLs (raw.githubusercontent.com) were reachable from this
  machine at verification time.
- Gesture: a real Playwright click on the deck.gl overlay (`#deckgl-overlay` canvas) landed on
  a city dot and the sidebar's "Selected city" card updated from `""` to `"Melekeok / Palau"`,
  confirming `selected()` fires on a genuine click and the server-rendered card reflects
  it (not just a client-side tooltip). Screenshots: `img/hero.webp`, `img/after_click.webp`.
- Did not re-verify the `city_radius`/`by_pop` in-place restyle or the `fly_to` button in this
  pass (already covered by the lonboard guide's own verification); only the accessor-driven
  click was re-driven here since that's the one most relevant to the showcase's "wow" factor.

## Judgment calls

- No changes needed beyond the run-command header line; the app was already clean (no
  `__doc__` trick, already `#`-comment header).
