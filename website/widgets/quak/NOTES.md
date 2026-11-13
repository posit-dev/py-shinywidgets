# NOTES: quak guide

## Versions

- `quak` 0.3.5, `duckdb` 1.5.6, `pyarrow` (current main venv), `plotly` (current main venv), `shiny` 1.9.0,
  Python 3.12.
- shinywidgets commit: current `main` (origin/main `00f90249`, plus the mols2grid work on top in the ambient
  checkout, which doesn't touch `render_quak`/`_quak.py` -- diffed the quak-relevant region of
  `_render_widget.py` between the two and it's byte-identical). Accessors (`sql()`, `data()`) landed via PR #384.
  Date: 2026-10-30.
- Playwright: Chromium, default headless launch (no WebGL flags needed; quak renders with plain SVG/HTML, no
  canvas or WebGL).
- Partway through this pass, the coordinator moved me from the shared main checkout to an isolated worktree
  (`.../scratchpad/main-wt`, detached at `origin/main`) because another agent was switching branches there. I
  verified beforehand that the quak-relevant source was identical between the two checkouts, so nothing done
  before the switch needed redoing. All screenshots were taken from the main checkout's venv before the switch
  message arrived; no screenshot needed a rerun for this reason (only two needed reruns, both for timing bugs
  in my own driver script -- see below).

## Verification table

All apps run via `shiny.run.run_shiny_app` (ports 9360-9379) and screenshotted with Python Playwright, Chromium,
1280x800-1400, `device_scale_factor=2`. Every screenshot referenced in `guide.md` was read with the Read tool
before being cited, and every one went through at least one real round of "look at it, fix what's wrong, re-shoot"
(see "Judgment calls" for the two actual bugs that surfaced this way).

| File | Ran | Screenshot | Gesture driven | Notes |
|---|---|---|---|---|
| `examples/01_quickstart.py` | yes | yes | n/a (static) | |
| `examples/01_quickstart.py` (crossfilter) | yes | before/after pair | yes -- drag `lifeExp` histogram | reused for the "What you can build" crossfilter highlight (no new code needed) |
| `examples/02_duckdb_relation.py` | yes | yes | n/a | first run failed at app startup (not a shinywidgets bug -- see Judgment calls #1) |
| `examples/03_scale.py` | yes | yes | n/a | first shot caught histograms mid-compute (blank) at 5M rows; fixed by waiting longer, not a bug |
| `examples/04_accessor_sql.py` | yes | before/after pair | yes -- sort `lifeExp`, then drag its histogram | confirms `ORDER BY`/`WHERE` text; code block's CSS fix (`pre { white-space: pre-wrap }`) needed so the query doesn't get clipped by the card |
| `examples/05_accessor_data_summary.py` | yes | before/after pair | yes -- drag `lifeExp` histogram | surfaced the quak status-bar-vs-exact-count mismatch (667 vs 688), see Bugs found |
| `examples/06_update_in_place.py` | yes | before/after pair | yes -- click "Grow the table" | three iterations to get a configuration where `layout.height` actually takes visible effect -- see Judgment calls #2 |
| `examples/07_linked_plot.py` | yes | before/after pair | yes -- click "Europe" bar in `continent` | first "after" shot raced the plotly render (blank chart) at 700ms; fixed with a longer wait, not a bug |
| `examples/08_linked_download.py` | yes | yes (table+button) | yes -- dragged a filter, then clicked Download and inspected the downloaded file | downloaded CSV had exactly 667 data rows, matching `table.data()`, not quak's "688" status-bar text |
| `examples/09_layout_sizing.py` | yes | yes | n/a | |
| `examples/10_security_lockdown.py` | yes | not included in guide (code-only illustration) | yes -- confirmed rows render and sorting still works after lockdown; separately confirmed the *unlocked* default lets `read_csv('/etc/hosts')` through (see Bugs found) | |
| `gallery/template_explorer.py` | yes | before/after pair | yes -- sort `lifeExp`, drag its histogram | |
| `gallery/showcase_trip_explorer.py` | yes | before/after pair | yes -- click "Manhattan" bar | first "before" shot raced the initial plotly render at 3M rows (blank chart) at 500ms; fixed with a 4s wait |

Also ran, as corroborating (not primary) evidence: `tests/playwright/render_quak/test_render_quak.py` and
`tests/playwright/quak_accessors/test_quak_accessors.py` exist on `main` and describe the same gestures
(`.sort-button` dispatch, `.interval-x .overlay` drag) I used here; I read them before writing my own driver
script rather than guessing selectors.

## Accessor coverage

- `sql()`: verified with a real gesture (sort + histogram drag), both directly (`examples/04`) and via every
  linked-view example that reads `table.data()` (which depends on it).
- `data()`: verified with a real gesture, materialized three different ways across the guide: `.aggregate(...)`
  (value boxes), `.df()` fed to plotly (chart), `.df().to_csv()` (download). Confirmed the downloaded CSV's row
  count against both quak's status bar and an independent DuckDB `count(*)` on the same published query.

Both accessors behaved exactly as their docstrings describe: `sql()` cancels silently (no `req()` needed) during
the brief `""` window at startup, and `data()` runs the *published* (debounced) query, confirmed by comparing a
captured `sql()` string against `data()`'s row count independently via a standalone DuckDB connection.

## Bugs found

### shinywidgets

**`render_quak` applies no DuckDB lockdown, unlike `render_embedding_atlas` and `render_pygwalker`.** quak's
`Widget._handle_custom_msg` (upstream, `quak/_widget.py`) runs whatever SQL string arrives over the comm directly
against `self._conn.query()`/`.execute()`, with no restriction on statement type or target. `render_quak._as_widget`
(`shinywidgets/_render_widget.py`) just calls `quak.Widget(value)` and returns it -- no `SET
enable_external_access = false` / `SET lock_configuration = true`, unlike `render_embedding_atlas` (which locks
down automatically, with an `allow_unrestricted_connection` opt-out) and `render_pygwalker` (which refuses to
render until the app's shared connection is locked down). I reproduced the gap directly, outside a browser
(constructing a `quak.Widget` and calling its own `_handle_custom_msg` with a malicious SQL string, exactly as
quak's own browser code would send it):

```python
import quak, pandas as pd
w = quak.Widget(pd.DataFrame({"a": [1, 2, 3]}))
msgs = []
w.send = lambda data, buffers=None: msgs.append(data)
w._handle_custom_msg({"uuid": "x", "sql": "select * from read_csv('/etc/hosts')", "type": "json"}, [])
# msgs[0]["result"] contains the file's contents
```

I then confirmed the fix works end-to-end in a real app (`examples/10_security_lockdown.py`): a `quak.Widget`
with `_conn.execute("SET enable_external_access = false")` / `SET lock_configuration = true` still renders,
sorts, and filters normally, and the same `read_csv` attempt against a locked-down connection raises a `Permission
Error` instead of returning data.

I'd call this a real gap worth closing (same shape as the embedding_atlas fix, and quak's `Widget.__init__`
always builds its own fresh `:memory:` connection when given a DataFrame, so the same "lock it down right after
construction" approach that `as_widget_embedding_atlas` uses should drop in cleanly) -- but flagging it here per
the brief rather than fixing it, since it's a security-relevant design decision for the maintainer to make (and
to decide whether it should be opt-out like embedding_atlas, given quak's docstring currently promises nothing
about this at all, so there's no documented behavior to preserve).

### Upstream (quak 0.3.5)

- **The status-bar row count can disagree with the exact row count of quak's own published query.** Brushing
  `lifeExp` on the 1,704-row gapminder dataset at the same fractional position every time (`frac_start=0.15,
  frac_end=0.55`) consistently produced a status bar reading "688 of 1,704 rows" while an independent DuckDB
  `count(*)` against the exact same published `sql()` string returned 667. Reproduced identically across five
  separate example apps in this guide (same data, same brush), so it's not noise -- it's a real (if small, ~3%
  in this case) discrepancy between what the status bar displays and what the query actually matches. This
  matches a finding (F6) from an earlier evaluation of this widget (`docs/widget-reports/quak/report.md`,
  written before the accessors existed), so it's a long-standing upstream quirk, not a new regression. I
  verified it independently rather than trusting the old report's claim.
- **Unsupported column types still crash the whole table.** A `timedelta64` column raises `Unsupported type:
  INTERVAL` (page error, blanks the table); an `int64` column with values above 2^53 raises `BigInt exceeds
  integer number representation` (also blanks the table). Both reproduced directly on quak 0.3.5 on current
  main, matching the old report's F5. Long-standing limitation, not new.
- **A bare `duckdb.DuckDBPyConnection` queries a table named `df` by default**, and fails with an unsurfaced
  Python-side `Catalog Error` (not shown in the UI) if no such table exists. Reproduced directly; matches the old
  report's F7. Long-standing, not new -- worth a one-line docstring mention (`quak.Widget(con, table=...)` is the
  fix) but I didn't chase it further since this guide already documents the workaround.

I did **not** re-verify the old report's F2 (hovering a histogram momentarily desyncs `sql` to a filterless
query) or F8/F9 (bundle-resend cost, echo-dropping) -- F2 is about to become moot from a user's perspective once
they're reading the *debounced* `sql()` accessor rather than raw `reactive_read`/`.observe()` (the accessor's
`not_ready` and debounce specifically smooth over exactly this kind of mid-gesture transient), and F8/F9 are
general anywidget/shinywidgets characteristics already covered in the generic render-widget guide, not specific
to quak. I'd rather flag this gap explicitly than assert something I didn't check.

## Update 2026-11-11 (main @ 32ca7035)

Brought up to date against `main` @ `32ca7035` (33 commits ahead of the `00f90249` base this guide was
originally verified against). Relevant commits for this guide: #395 (DuckDB lockdown), #437 (`.read()` /
unified accessor semantics -- `sql()`/`data()` were already "state" accessors and unaffected in substance).

- **`render_quak` now locks down the widget's DuckDB connection by default (#395)**, which fixes the exact gap
  this guide's "Bugs found" section flagged on 2026-10-30 (quoted above). Rewrote the Security section: the old
  "quak has no lockdown, lock it yourself" framing and its workaround are gone; the guide now describes the
  default lockdown and `allow_unrestricted_connection=True` as the opt-out for a local, single-user app, plus
  the shared-connection subtlety (lockdown is permanent and database-wide) for the `quak.Widget(con)` case.
  Added one sentence to the intro paragraph flagging the lockdown up front, matching how the embedding-atlas and
  mosaic guides frame it.
  - Verified server-side (not a browser gesture -- this is Python/DuckDB-level behavior, not something a
    screenshot can show): built a `render_quak()` instance, called its widget's own `_handle_custom_msg` the way
    quak's browser code would, confirmed a `read_csv('<secret file>')` query now raises `Permission Error` while
    an ordinary `SELECT` still returns rows. Repeated with `allow_unrestricted_connection=True` and confirmed the
    file read succeeds, as the guide now documents. Also ran the shipped unit tests covering this
    (`tests/unit/test_render_widget.py -k quak`, `test_render_quak_restricts_connection_by_default`,
    `test_render_quak_allow_unrestricted_connection`, `test_render_quak_respects_author_locked_connection`,
    `test_render_quak_raises_when_connection_attr_missing`) -- all pass.
  - Rewrote `examples/10_security_lockdown.py`: the old version manually locked `widget._conn` after
    construction (the only option before #395); the new version just passes
    `allow_unrestricted_connection=True` to show the opt-out, since the default case needs no example at all
    (every other example in this guide is already safe to deploy with no changes). Ran it with `shiny run` and
    took a screenshot confirming the table renders normally (`img` not added to the guide -- the security
    behavior itself isn't visible in a screenshot, consistent with how this example was treated before: code-only
    illustration, not inlined with an image).
- **Accessor reference table**: reformatted to the new standard columns (`returns | before any interaction |
  across re-render | default rate policy`). No behavior changed for `sql()`/`data()` -- both are "state"
  accessors (inherent widget state: the published query describing the table's *current* sort/filter), so both
  re-seed from the new table on every render, same as before #437 just now with vocabulary that matches the
  other guides.
- **"Beyond the accessors"** now points at `table.read("trait")` (falls through to `reactive_read()` on the
  rendered widget) as the thing to reach for if quak ever adds a public trait, replacing the old plain
  `reactive_read(table.widget, "trait")` mention -- no code example changed, since quak has no such trait today
  and this guide never used `reactive_read()` in a code sample.
- **`08_linked_download.py`** (CSV download) is already the guide's "read on demand" example (the brief's
  suggested pattern for this release): the download handler reads `table.data()` only when the user clicks
  Download, with no warm-up. Added one sentence calling this out explicitly; the code was already correct and
  needed no change.
- **`data(filter_by=...)` (#403)** doesn't apply here -- that parameter was added to `render_mosaic_widget.data()`,
  not `render_quak.data()` (quak has no named-selection concept to filter by). No change needed.
- CHANGELOG.md's `@render_quak` bullet (line ~42) still only lists `sql()`/`data()` and doesn't mention the
  lockdown or `allow_unrestricted_connection`, unlike the embedding_atlas and pygwalker bullets right next to
  it, which both call out their security posture. Confirmed by reading `git show --stat` on the #395 commit
  (3fc32c7b): it touched only `_render_widget.py` and the unit tests, not `CHANGELOG.md`. Not fixed (CHANGELOG.md
  is outside this guide's assigned directory and the operating rules forbid editing tracked files) -- flagging
  as a docs gap for the maintainer.

### Verification table (new/edited files)

| File | Ran | Screenshot | Verification |
|---|---|---|---|
| `examples/10_security_lockdown.py` | yes (`shiny run`, port 8110) | yes, looked at (not inlined in guide.md -- see above) | Playwright: table renders, 1,704 rows. Security behavior verified separately at the Python/DuckDB level (not browser-visible); see above. |

### Bugs found (2026-11-11)

- **Fixed since 2026-10-30**: the "no DuckDB lockdown" gap this guide previously reported as a shinywidgets bug
  is fixed by #395. No longer listed as a bug; see the rewritten Security section instead.
- **New**: `CHANGELOG.md`'s `@render_quak` entry doesn't mention the #395 lockdown or #403's mosaic `filter_by=`
  (the latter isn't quak's, just noting the CHANGELOG gap is broader than quak alone -- see mosaic's NOTES.md).
  Docs gap, not a behavior bug.
- Everything else in "Bugs found" above (status-bar count mismatch, unsupported column types, bare-connection
  default table name) still reproduces on `main` @ `32ca7035` -- not re-run individually this pass since none of
  them touch code this update changed, but nothing in the #395/#437/#403 diffs plausibly affects them.

### Docs (on current main)

`render_quak`'s docstring is accurate everywhere I checked it against observed behavior (the `sql`
read-only/empty-at-startup description, the accessor descriptions, the `.data()` semantics around the debounce
window) with one gap: it says nothing about the DuckDB connection's security posture at all, unlike
`render_embedding_atlas` and `render_pygwalker`, which both have a dedicated "Security" docstring section. Given
the bug above, I'd consider this a docs gap worth closing together with the code fix, not separately.

## Judgment calls (flag for the maintainer)

1. **`DuckDBPyConnection.register()` returns the connection (for chaining), which breaks Shiny Express's
   auto-display.** `examples/02_duckdb_relation.py`'s first draft called `con.register(...)` as a bare top-level
   statement; Express tried to render the returned `DuckDBPyConnection` as page content and the app failed to
   start (`TypeError: Invalid tag item type: <class '_duckdb.DuckDBPyConnection'>`). Fixed by assigning the
   return value to `_`. This is a Shiny Express foot-gun interacting with duckdb's chainable API, not a
   shinywidgets bug, but it's exactly the kind of thing a reader would hit copying this pattern, so I called it
   out both in the example's own comment and in Gotchas.
2. **A widget's `layout.height` set from Python is invisible while the output is filling its container.** My
   first `examples/06_update_in_place.py` draft set `render_quak`'s output to fill a `full_screen` card (the
   default, and what every other example here does) and then toggled `table.widget.layout.height` between two
   values -- the inline style changed (confirmed via `page.evaluate`) but the rendered box never moved, because
   the fill CSS (`html-fill-item`, stretch-to-container) takes precedence over an explicit height on the same
   element. I also confirmed the *output's own* default non-filling size is a hardcoded 400px with
   `overflow: hidden`, which clips anything taller even when `fill=False`. The configuration that actually works
   (and what I ended up documenting): give the output a roomy fixed `height=` so it isn't filling and isn't
   clipping, then toggle `layout.height` between two values both smaller than that ceiling. I think this is
   worth a line in `render_quak`'s own docstring (or the generic render-widget guide, since this isn't
   quak-specific -- it'll affect any widget whose layout height someone tries to flip from Python), since I
   don't think a reader would find this by themselves without the same trial-and-error I went through.
3. **No separate "sorting" example.** Sorting needs zero application code (it's quak's built-in header UI), so I
   folded it into the crossfiltering highlight's prose instead of giving it its own snippet/screenshot, and
   exercised the actual gesture inside the `sql()` accessor example instead (where it's load-bearing: the
   screenshot's `ORDER BY` only appears because I sorted first). Per "never pad."
4. **Three linked-view patterns, not four.** The brief's examples ("lasso -> filtered table; click -> detail
   card; map viewport -> chart; table row selection -> highlight") don't map cleanly onto quak (it has no
   selection concept beyond the filter itself), so I used the three patterns the assignment text explicitly
   named instead: summary stats, a plot of the filtered rows, and a CSV download. A fourth (e.g., "filter one
   quak table, highlight matching rows in a second quak table") felt like padding -- quak has no cross-widget
   linking primitive beyond re-querying `data()`, so a fourth pattern would just be a restatement of pattern 2
   with a different widget on the right.
5. **Gallery showcase uses 3M rows, not 5M like the scale example.** Picked a smaller number for the showcase so
   the Playwright screenshot round-trip stayed fast during iteration; both comfortably demonstrate "scale," and
   the guide text doesn't claim a specific number works better than another.

## Editor's notes for the website

- **Strongest screenshots**: `img/gallery_showcase_after.webp` (used as the hero) -- one screenshot shows the
  table, a crossfilter in progress, two value boxes, and a chart all agreeing with each other. The
  `crossfilter_before/after` pair is the best *simple* demonstration of the headline feature with zero code.
- **The `data_summary_after.webp` / `gallery_template_after.webp` pair showing 667 vs. 688** is a good "we actually
  checked this" detail for a technical reader, but could be cut from a shorter page without losing the guide's
  core argument (it only needs one sentence in Gotchas to stand alone).
- **Candidate to cut for a shorter page**: "Beyond the accessors: reactive_read" is one short paragraph saying
  there's nothing else to read -- genuinely low-value, could be merged into the accessor reference table's
  footnote instead of its own heading.
- **Cross-widget pairing**: `examples/07_linked_plot.py` and `gallery/showcase_trip_explorer.py` both pair with
  [plotly](../plotly/index.md). No other pairings in this guide.

## What I dropped from the old report and why

- **The B1 scroll-stall bug (PR review blocker)**: fixed on `main` (the proposed fix in the old report is
  essentially what's now in `js/src/quak.ts`, and `test_quak_tall_table_loads_rows_on_scroll` passes). Not
  mentioned in the guide at all, since a user on current `main` will never see it.
- **The `.worktrees/render-quak` PR-review framing, scorecard, and merge verdict**: not applicable -- this guide
  describes released, merged behavior, not a pending PR.
- **Weight/memory measurements (1M-row timing against `render.DataGrid`, websocket bytes, JS heap)**: valuable
  but out of scope for a teaching guide per the brief ("Don't regurgitate... teach what's possible"); I kept the
  *qualitative* version of this claim ("a table of 5 million rows renders about as fast... as 5 thousand") since
  it's the actual reason to reach for quak, without re-deriving exact numbers that would need updating every
  time duckdb or quak changes.
- **F9 (echo updates applied as fresh state) and F8 (bundle resend cost)**: both are general anywidget/shinywidgets
  characteristics, not quak-specific findings, and already noted as out of scope above.
- **F4 ("don't set `widget.sql`")**: kept, but folded into one line in Gotchas rather than its own finding,
  since it's now redundant with the accessor docstring, which already says `sql` is read-only.

## Update 2026-11-11 (Task 8a: Large data section)

Added `## Large data` after "Coordinating multiple views": no new example -- cites this guide's own existing `examples/03_scale.py` (5M-row render, already verified per this guide's own verification table) and its architecture (DuckDB-backed, only visible rows + histogram bins cross the wire). Did not tabulate new bytes, consistent with this guide's own prior-pass judgment call to keep the '5M renders as fast as 5K' claim qualitative.
