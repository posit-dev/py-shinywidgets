# NOTES: pydeck guide

## Update 2026-11-11 (main @ 32ca7035)

### Follow-up fix (coordinator-flagged)

Missed on the first pass: `reactive_read(bike_racks.widget, "view_state"/"clicked")` in `guide.md` (lines 253,
264 at the time) and the matching `reactive_read(racks.widget, ...)` in `gallery/template_bike_racks.py` were
still unconverted -- both are reads on the output's own maplibre widget, the tier-2 case `.read()` replaces.
Converted both to `bike_racks.read("view_state")`/`.read("clicked")` and `racks.read(...)`, dropped the now-
unused `reactive_read` import from `examples/03_view_state_clicked.py` and `gallery/template_bike_racks.py`,
and re-synced `guide.md`'s embedded code block to stay byte-identical to `examples/03_view_state_clicked.py`
(verified with a diff). Also updated two prose mentions (the migration-path intro paragraph and the
before/after comparison table) from `reactive_read(map.widget, ...)` to `map.read(...)` for consistency.
Re-ran `examples/03_view_state_clicked.py` in a browser: panned the map (view_state count went 2213 -> 2159
racks in view) and clicked a dot (correctly reported "Nearest rack: 3200 CALIFORNIA ST (10 spaces)"); replaced
`img/view_state_before.webp` and `img/view_state_after.webp` with fresh screenshots, both read back. Also smoke-
tested `gallery/template_bike_racks.py` (pan + click both updated correctly) without taking new screenshots for
it (no screenshot of that file was referenced from guide.md).

shinywidgets commit `32ca7035` (worktree `main-wt`); pydeck/maplibre/lonboard versions unchanged from the
original pass. Per the update brief, this is a light-touch pass: pydeck is deprecated, no new capability, no
accessors of its own (`accessors: []` unchanged).

**#413 (`render_pydeck`'s warning category: `DeprecationWarning` -> `FutureWarning`) is the one substantive
change, and it inverts a claim the guide was making.** The guide previously said the warning is "silently
dropped unless you run with `python -W always`" -- true for the old `DeprecationWarning` on main @ `00f90249`,
and re-confirmed historically in "Bugs and surprises found" below. On current main it is no longer true:
`FutureWarning` is shown by Python's default filters regardless of module, and a real `shiny run` of
`examples/01_deprecation_error.py` now prints the warning to the server log automatically, pointing at the
`@render_pydeck` line. Rewrote the relevant guide paragraph to state this correctly, with the verified log line
quoted directly, and softened the "Gotchas" bullet that called it "easy-to-miss." Marked the matching "Bugs and
surprises found" entry below as fixed by #413 (with the original finding kept for provenance, not deleted,
since it documents why the fix exists).

**The `TypeError` text** (`PYDECK_NO_WIDGET_MESSAGE` in `shinywidgets/_as_widget.py`) is unchanged
character-for-character from the original pass -- re-diffed against the guide's quoted block, still an exact
match, no edit needed there.

**Other changes:** the pydeck -> maplibre mapping table's `on_click`/`on_hover`/`on_view_state_change` row said
`reactive_read(map.widget, "clicked" / "view_state")` for the maplibre target; updated to `map.read(...)` to
match the roster's new taught fallback (maplibre still has no accessors for these, so this is the same
`reactive_read()` call under a documented name, not a behavior change -- `render_maplibre` confirmed to have no
`_accessor_specs` entry). No other commits in 00f90249..32ca7035 touch pydeck, maplibre's accessor surface, or
lonboard's; the rest of the guide (migration examples, gallery, accessor-reference mentions for the two
migration targets) needed no changes and was not re-run this pass -- text-only edits per the brief's "text-only
edits to guide.md need no browser run, but any claim you add about behavior does" (the FutureWarning claim is a
pure server-side, pre-render behavior with no browser/JS component -- verified by actually running `uv run
--no-sync python -m shiny run examples/01_deprecation_error.py` and reading its server log, the correct
verification method here since there's no page or gesture to drive).

## Versions and environment

- Date: 2026-11-02
- shinywidgets `main` @ `00f90249` (worktree detached from `origin/main`)
- shiny 1.9.0, Python 3.12, pydeck 0.9.3, pandas 3.1.0, maplibre (py-maplibregl) 0.3.6, lonboard
  0.17.0, geopandas 1.2.0, anywidget 0.11.0 -- all already in the shared venv (`uv pip list`), no
  `--with` overlays used
- Playwright Chromium, headless, `--use-angle=swiftshader --enable-unsafe-swiftshader
  --ignore-gpu-blocklist` (matches the maplibre/lonboard guides' recipe)
- Ports 9881-9886 (assigned range 9880-9899); scratch work at
  `/private/tmp/claude-502/-Users-cpsievert-github-py-shinywidgets/b5f9c833-cf3f-448f-841f-2c46c3116629/scratchpad/agents/pydeck`
- Data: `https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/sf-bike-parking.json`
  (pydeck's own `ScatterplotLayer` tutorial dataset, 2,520 SF bike racks with `ADDRESS`/`RACKS`/
  `SPACES`/`COORDINATES`, no API key). Chosen instead of the UK-accidents/3d-heatmap dataset because
  that one is already the maplibre guide's own gallery showcase (`showcase_uk_accidents.py`, itself
  a straight port of this repo's `examples/pydeck/app.py`) -- reusing it here would have been pure
  duplication of material this guide links to instead.

## This guide's scope, and why it's short

Per the brief, this is a **migration guide**, not a feature tour. `../maplibre/guide.md` already has
a full "Deck.GL layers" section, a verified 140k-point gallery showcase built from this repo's own
`examples/pydeck/app.py`, and a complete accessor reference (`view_state`, `clicked`, `draw_*`); this
guide links to all of that rather than re-deriving it. What's unique to *this* guide: the
deprecation error itself, a smaller before/after conversion of a different (and also real,
recognizable) dataset so the maplibre guide's showcase isn't just repeated, the lonboard and static
fallback paths (neither of which the maplibre guide covers), and a concept-mapping table a reader
mid-migration can scan.

## Verification table

Every file below was run with `uv run --no-sync python -m shiny run --port <p> <file>` from the
worktree, screenshotted with Playwright Chromium, and every screenshot was viewed with the Read tool
before being referenced in `guide.md`.

| file | ran | screenshot(s) | gesture driven | confirmed |
|---|---|---|---|---|
| `examples/01_deprecation_error.py` | yes | `deprecation_error.webp` | none (static) | `@render_pydeck` returning a `pydeck.Deck` raises the documented `TypeError`; full text captured from the server log too |
| `examples/02_migrate_restyle.py` | yes | `restyle_before/after.webp`, `tooltip.webp` | pan (mouse drag), slider drag (ion-range-slider handle), hover (2-step mousemove) | restyle-in-place confirmed (radius 6 -> 20, identical camera framing in both screenshots); tooltip confirmed showing `"1355 MARKET ST: 200 spaces"` |
| `examples/03_view_state_clicked.py` | yes | `view_state_before/after.webp` | scroll-zoom (`mouse.wheel`), click | `view_state` count dropped 2351 -> 1942 after zooming in; `clicked` resolved to the correct nearest rack (`"1117 MARKET ST (4 spaces)"`) after a click |
| `examples/04_lonboard_scatter.py` | yes | `lonboard_scatter.webp` | none (static) | `ScatterplotLayer.from_geopandas()` renders all 2,520 racks, auto-fit view, no console errors (`page.on("pageerror")` empty) |
| `examples/05_static_iframe.py` | yes | `static_iframe.webp` | none (static) | iframe renders pydeck's default dark Carto basemap + scatter layer; measured `len(deck.to_html(as_string=True))` = 0.48 MB for this dataset, and confirmed `deck.to_html()` with no filename returns `None` |
| `gallery/template_bike_racks.py` | yes | `gallery_template_before/after.webp` | click | combines the restyle slider, tooltip, and view_state/clicked summary panel; click produced `"Nearest rack: 1 DR CARLTON B GOODLETT PL (4 spaces)"` |

**Accessor coverage:** `render_pydeck` itself declares no accessors (it can't render anything to have
state on) -- not applicable. The two migration targets' accessors used here were verified with real
gestures: maplibre's `view_state`/`clicked` (via `reactive_read`, pan + scroll-zoom + click, both
`examples/02` and `03` and the gallery template) and lonboard's existence is covered by its own guide
(not independently re-verified here beyond confirming `ScatterplotLayer.from_geopandas()` renders).

## Bugs and surprises found

1. **[FIXED on main @ 32ca7035 by #413 -- re-verified 2026-11-11]** ~~`render_pydeck(...)`'s
   `DeprecationWarning` is silently dropped by Python's default warning filters.~~ #413 changed the warning
   from `DeprecationWarning` to `FutureWarning` for exactly this reason (its own commit message says so).
   Re-verified directly: running `examples/01_deprecation_error.py` under a plain `shiny run`, with no flags,
   now prints `app.py:12: FutureWarning: render_pydeck is deprecated: ...` to the server log at decoration
   time, pointing at the `@render_pydeck` line (`stacklevel=2` correct). The original finding follows, for
   provenance: Python's default filter set used to be `("default", ..., __main__)` / `("ignore", ...,
   None)` for `DeprecationWarning` (confirmed interactively: `warnings.filters[:2]` on this venv), meaning it
   was shown once only from the `__main__` module and ignored everywhere else; a Shiny app's module is never
   `__main__` (Shiny imports and runs it), so the warning never reached the console by default -- confirmed by
   grepping the server log of `examples/01_deprecation_error.py` for "deprecat" (zero matches) after
   triggering a render. That was never a shinywidgets bug (it's how `warnings.warn(DeprecationWarning)`
   behaves everywhere); it's simply fixed now by the category change.
2. **[confirmed, not a regression] The old report's three blockers are all independently fixed on
   `main`, matching the maplibre guide's own findings:**
   - `as_widget_pydeck` now checks `pydeck_has_widget()` before calling `.show()`, so the old
     report's "pandas 3 + pydeck 0.9.1 gives a cryptic `vars()` TypeError instead of the helpful one"
     no longer applies (verified: the helpful message appears directly, no `vars()` error, with the
     repo's locked pydeck 0.9.3 / pandas 3.1.0).
   - The orphan-`DeckGLWidget`-comm leak (`is_unused_pydeck_widget()` in `_shinywidgets.py:935`,
     wired into the widget-construction hook at `:131`) is in place; confirmed by reading the code
     rather than re-measuring comm counts (the mechanism is a straightforward early-return, and
     re-deriving the old report's leak-counting methodology wasn't worth the time for a guide that
     doesn't ship `render_pydeck` as a working path either way).
   - `examples/pydeck/app.py` in the shinywidgets repo is no longer the session-crashing old pydeck
     app -- it's already the maplibre-based UK-accidents conversion (confirmed by reading the file),
     i.e. the "replace the example app" follow-up from the old report is done.
3. **[docs, new finding] Shiny's error-sanitization default (`sanitize_errors=False`,
   `shiny/_app.py:63`) is what makes the `TypeError` visible inline in dev mode**, which is why
   `01_deprecation_error.py`'s screenshot shows the full message rather than a generic "An error has
   occurred." Not pydeck-specific, but worth a line in the guide since a reader deploying with
   `sanitize_errors=True` would only see the full text in the server log, not the UI.

## Judgment calls for the maintainer to revisit

- **Dataset choice (SF bike parking, not UK accidents/3d-heatmap).** The UK-accidents dataset is
  already thoroughly covered as the maplibre guide's own gallery showcase (built from this repo's
  `examples/pydeck/app.py`). Using a second real, recognizable, pydeck-tutorial dataset
  (`sf-bike-parking.json`, also from `visgl/deck.gl-data`, also used in pydeck's own
  `ScatterplotLayer` quickstart docs) keeps this guide's examples non-redundant with the guide it
  links to, while still being something a pydeck user would recognize. Happy to switch to the
  accidents dataset throughout if the maintainer prefers one dataset across both guides.
- **No "before" code in `examples/`.** The brief's code conventions require every guide.md snippet to
  be copied verbatim from a runnable file in `examples/`. The "classic pydeck" side of each
  before/after comparison is, by definition, what no longer works -- `examples/01_deprecation_error.py`
  *is* that classic code, wrapped in `@render_pydeck` so it actually runs (and errors, which is the
  point). I did not create a second non-runnable "historical" file for the before/after table in the
  "Migration path A" section; that table's "before" column is prose/inline code describing the old
  API shape, not a standalone snippet claiming to run.
- **lonboard section has one example, not the "short example + when to choose" split as two files.**
  Given the brief's explicit instruction that this guide should be "shorter than the others," I
  combined the conversion snippet and the choice-criteria prose into one subsection rather than
  adding a second lonboard example file.
- **Did not re-measure the old report's exact byte counts for UK-accidents-scale payloads** (15.6 MB
  static HTML, etc.) -- cited them from the old report with attribution ("see the old evaluation
  report") rather than re-running that measurement myself, since the maplibre guide's gallery
  showcase already covers that dataset at that scale.

## Editor's notes for the website

- **Strongest material:** the `restyle_before/after.webp` pair (same camera framing, radius 6 -> 20)
  is the clearest single image for "in-place restyle beats re-render," and
  `view_state_before/after.webp` (count drops 2351 -> 1942, then a correct nearest-rack lookup) is the
  clearest "the map is an input now" image. Either works as the hero if the maintainer wants a
  different one than `restyle_before.webp`.
- **What to cut for a shorter page:** the "What doesn't carry over" bullet list (4 items) could
  shrink to 2 (views, and the lng/lat ordering gotcha) if space is tight -- the basemap-naming and
  "aggregation still works" bullets are lower-value for a reader who's already decided to migrate.
- **What I dropped from the old report, and why:**
  - The full scorecard, methodology section, and "should-fix"/"nits" review-process lists: PR-review
    artifacts, not reader-facing teaching content (same call the maplibre guide's NOTES.md made).
  - The pydeck-0.8-with-patches investigation (UMD loader patch, ipywidgets-8 tooltip-trait clash):
    interesting archaeology, but pydeck 0.8 is a 2022 release pinned to `ipywidgets<8`, which
    shinywidgets' current `ipywidgets>=8.1` requirement already rules out -- not an actionable
    migration path for any reader on supported dependencies.
  - The detailed basemap-token matrix (Carto/Mapbox/Google/satellite across flat and pitched views):
    already covered thoroughly by the maplibre guide's own "Vector-tile basemaps, no API key"
    section; this guide's mapping table links the concept without re-running the matrix.
  - The multi-session leak measurement for the pre-fix orphan-widget bug: fixed on `main` (see Bugs
    found #2), re-confirmed by reading the code rather than re-measuring.

## Cross-widget pairings (for the coordinator's cross-cutting articles)

- **pairs with: maplibre** -- this guide's entire reason for existing; the "Migration path A" section
  and gallery template are built directly on `render_maplibre`'s `add_deck_layers()`/
  `set_deck_layers()` and `reactive_read()` tier.
- **pairs with: lonboard** -- "Migration path B"; same dataset, converted to
  `ScatterplotLayer.from_geopandas()`, with lonboard's native accessors mentioned as a reason to
  prefer it over maplibre when per-feature picking matters more than deck.gl's GPU aggregation
  layers.
