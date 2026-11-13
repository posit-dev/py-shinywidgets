# NOTES: AI-assisted exploration with widgets

## Versions

- Date: 2026-11-02
- shinywidgets: `0.8.2.post1.dev102+g00f90249` (worktree detached at `origin/main`,
  commit `00f90249`, 2026-10-30)
- shiny 1.9.0, shinychat 0.7.2, plotly 6.9.0, itables 2.9.1, ipyleaflet 0.20.0,
  pandas 3.1.0, duckdb 1.5.6 (all already in the locked venv)
- querychat 0.9.0, chatlas 0.23.0, anthropic 2.3.0 (not in the locked venv; installed as
  `uv run --no-sync --with querychat --with chatlas --with anthropic python -m shiny
  run ...` overlays, confirmed unpinned versions above are what actually resolved)
- Model: `claude-haiku-5-5` (Anthropic), via `chatlas.ChatAnthropic`, in every example.
  Real API calls throughout -- no mocking. Total verification cost for this article was
  well under $0.05 (small system prompts, short tool schemas, ~20 total chat turns
  across every driver run while debugging example 2's flake, below).

## Verification table

| File | Ran in browser | Screenshot | Gesture driven | Real LLM call | Notes |
|---|---|---|---|---|---|
| `examples/01_querychat_to_widgets.py` | yes | before/after | typed a querychat question via Playwright + `shinychat.playwright.ChatController` | yes (querychat's own client) | chart recolor + table re-render both confirmed |
| `examples/02_selection_to_chat_context.py` | yes | before/lasso/after | real plotly lasso drag (Playwright mouse events) + typed chat question | yes | see "Accessor attach" finding below; verified reliable only after adding the warm-up effect |
| `examples/03_llm_tool_drives_map.py` | yes | before/after | typed chat requests (valid city + an invalid/path-traversal-shaped one) | yes | `fly_to` tool call confirmed via shinychat's "Used `fly_to`" disclosure and the map actually recentering |
| `examples/04_map_chart_chat_combined.py` | yes | before/after fly_to | typed chat requests (`summarize_view`, then `fly_to`, then `summarize_view` again) | yes | chart and chat answers cross-checked against each other (249 pods matched the chart's bar heights; after `fly_to`, both agreed on 1 visible pod) |

All four apps were run from the coordinator's worktree
(`scratchpad/main-wt`) on ports 10040-10043, one server and one headless Chromium
instance at a time, per the operating rules. Screenshots: Playwright Chromium,
1280x800, `device_scale_factor=2`.

## Representative transcripts

**Example 1** (querychat), question: *"just the countries in the Americas with gdp per
capita over 20000"* &rarr; querychat replied: *"The dashboard now shows only the Americas
countries with GDP per capita above $20,000."* and ran
`SELECT * FROM gapminder WHERE continent = 'Americas' AND gdpPercap > 20000` (2
countries: Canada, United States) -- both appeared highlighted on the chart and in the
table.

**Example 2** (selection &rarr; chat context), question: *"What's special about the points
I selected?"* after lassoing the high-income cluster (28 countries) &rarr; *"Your
selection is a cluster of wealthy, long-lived countries: the average GDP per capita is
about \$31,400 and average life expectancy is about 79.8 years... It is dominated by
Europe (18 of 28), with 5 from Asia and 3 from the Americas."* -- every number matches
the summary string computed server-side; the model added no numbers of its own.

**Example 3** (tool calls a map), *"fly to nairobi please"* &rarr; *"Used `fly_to`. The map
is now on Nairobi, zoomed to level 11."* -- map recentered on Nairobi. Then *"fly to
../../etc/passwd"* &rarr; the tool itself returned `"Unknown city '../../etc/passwd'.
Valid cities: paris, tokyo, nairobi, san francisco."`, which the model relayed instead of
touching the map.

**Example 4** (combined), *"what's visible on the map right now?"* &rarr; *"Used
`summarize_view`. There are 249 car-share pods visible on the map right now. By time of
day, that breaks down to 127 at night, 38 in the morning, 33 in the afternoon, and 51 in
the evening."* (matches the bar chart exactly, since both read the same `map.bounds()`).
Then *"fly to the west island"* &rarr; map recentered, bar chart dropped to one bar
(evening, count 1). Then *"now what's visible?"* &rarr; *"Only one pod is visible from
the West Island view, and it's an evening pod."*

## Bugs found

**Status as of 2026-11-11 (main @ 32ca7035): fixed by #437.** The finding below is kept
as the original repro and history; see "Update 2026-11-11" further down for the
re-verification that it no longer reproduces.

### [sw, design gap, surfaced by this article] Event accessors attach lazily on first read, which a gated chat handler can miss

`shinywidgets/_accessors.py`'s `Accessors.on_render()` only attaches a non-`eager`
accessor's browser-side listener if `slot.activated` is already `True` from a prior
render; `Accessors.read()` is what sets `slot.activated = True`, by calling `_attach()`
on first read. `AccessorSpec`'s own docstring names exactly this risk ("Attach during
render rather than on first read, for widgets whose events are lost unless a handler
exists before the view is created") -- several renderers already opt in
(`render_ipycytoscape`'s `clicked_node`/`clicked_edge`, `render_rerun`'s `selection`,
`render_mols2grid`'s `clicked`), but `render_plotly`'s `selected()` (used in example 2)
and `render_ipyleaflet`'s `bounds()` (used in example 4) do not.

In an app where *something* visible reads the accessor on first render (every other
guide's examples, because the guide itself displays the accessor's value), this is
invisible. This article's pattern breaks that assumption: `chat.on_user_submit` and a
registered tool are exactly the kind of code that reads an accessor for the first time
only *after* the user has already interacted with the widget the gesture that triggers
the handler. Reproduced directly: example 2's lasso-then-ask flow, with no warm-up read,
lost the selection in 2 of 3 trials (confirmed with a temporary `@reactive.effect` that
printed `plot.selected()` to the server log: `None` both times the chat reported "nothing
selected", `28` both times a `@reactive.effect` already existed to attach the listener
early). With a one-line `@reactive.effect` reading `plot.selected()` unconditionally at
startup (kept in the shipped example), 3 consecutive full runs (lasso + ask) all
succeeded. The same fix is applied to example 4's `map.bounds()`.

This is **not a race/timing issue** -- waiting longer (tested up to 4.5s after the
gesture, well beyond any plausible websocket latency) did not help without the warm-up
read; adding the warm-up read fixed it regardless of wait time. The browser-side lasso
visibly completed identically (dashed selection box, dimmed non-selected points) in both
the failing and succeeding cases -- the difference is purely whether *something* had
already attached the listener before the gesture happened.

**Recommendation for the maintainer**: either mark `render_plotly`'s event accessors (and
similarly-shaped ones on other renderers) `eager=True` by default, or add a line to every
event accessor's docstring recommending a startup warm-up read when the only planned
reader is itself gated behind user input (a chat handler, a button-triggered effect,
etc.). The `eager` escape hatch already exists and already works -- `render_ipyleaflet`'s
`clicked()` is `eager=False` too and would have the identical hazard were an app built
the same way around it instead of `bounds()`.

**Update (Decision 3b, adopted)**: `AccessorSpec.eager` now defaults to `True` for
`kind="state"` accessors (they attach at render, so `render_ipyleaflet`'s `bounds()`
no longer needs a warm-up read) and stays `False` for `kind="event"` accessors, whose
docs now recommend the startup warm-up read idiom described here.

### No other shinywidgets bugs found in this article's scope

querychat's own SQL safety (DuckDB `enable_external_access = false`,
`disabled_filesystems = 'LocalFileSystem'`, autoload/autoinstall of extensions off, lock
configuration, plus a `check_query()` allowlist that always blocks
DELETE/TRUNCATE/CREATE/DROP/ALTER/GRANT/REVOKE/EXEC/EXECUTE/CALL and blocks
INSERT/UPDATE/MERGE/REPLACE/UPSERT unless `QUERYCHAT_ENABLE_UPDATE_QUERIES=true`) was
read directly from the installed package (`querychat/_datasource.py`'s
`duckdb_lock_down()`, `querychat/_utils.py`'s `check_query()`) and is unrelated to, and
unaffected by, the quak/mosaic finding already in `FINDINGS.md` (those renderers execute
*browser-sent* SQL through an *unlocked* connection; querychat locks its own connection
regardless of who's asking).

## Judgment calls

- **Model choice**: `claude-haiku-5-5` throughout, per the assignment's suggestion.
  Tool-calling and short analytical answers (2-3 sentences, per each example's system
  prompt) worked well at this tier; no example needed a larger model.
- **`querychat.express.QueryChat` vs. the plain `querychat.QueryChat`**: the plain class
  (`from querychat import QueryChat`) has no `.df()` method at all in a Shiny Express
  script -- it's built for core Shiny apps and expects an explicit `.server(...)` call
  returning a `ServerValues` object. `querychat.express.QueryChat` auto-calls `.server()`
  and exposes `.df()`/`.sql`/`.title` directly, which is what every other example in this
  roster expects from "a reactive value." This cost real debugging time (an
  `AttributeError: 'QueryChat' object has no attribute 'df'` from the wrong class) and is
  worth a one-line callout in querychat's own docs if a future pass touches them.
- **`chat.stream_async(...)` must be awaited to get the generator**: `chatlas.Chat.stream_async`
  is declared `async def` and returns an `AsyncGenerator`, which means you must
  `await chat_client.stream_async(prompt)` to get the generator before iterating it (or
  passing it to `chat.append_message_stream`) -- passing the un-awaited coroutine raises
  `TypeError: wrap_async_iterable requires an Iterable object.` inside shinychat, not
  inside chatlas, which took a moment to trace back. This matches chatlas's own
  docstring example (`await chat.stream_async(...)` inside a list comprehension) once
  found, but is easy to miss on a first read of the type hint alone.
- **`shinychat.Chat.transform_user_input()` is removed** in the installed
  shinychat 0.7.2 (`raise TypeError("... has been removed. Instead, transform user input
  manually before passing it to your LLM provider")`), despite being a plausible-sounding
  API for exactly example 2's use case. Example 2 instead drives the chat manually with
  `@chat.on_user_submit`, which is shinychat's own documented replacement pattern.
- **Example 4 is a showcase candidate, kept in `examples/`**: it combines a map, a
  reactively-updating chart, and two tools, and is independently verified end to end, but
  it is single-purpose (one hardcoded place list, no error recovery beyond the
  allow-list message, no "lasso" gesture as the brief's suggested arc literally
  describes -- ipyleaflet has no lasso, so this uses pan/zoom + `bounds()` instead, the
  same shape). Left for the maintainer to decide whether it's worth polishing into
  `gallery/showcases/` (e.g., with a richer place list, a second widget pairing, or an
  actual lasso-capable chart alongside the map) rather than promoting it as-is.
- **Why gapminder/carshare for all four examples**: both are already used, verified, and
  screenshotted in `reacting-to-widgets` and `linked-views`, so this article's
  screenshots are visually consistent with the rest of the roster and the data's
  shape (what a "cluster," a "region," "visible pods" mean) doesn't need re-explaining.

## Editor's notes for the website

- Strongest section: example 2's "selection &rarr; chat context" screenshots and the
  accessor-attach finding -- it's a real bug with a precise repro and a one-line fix,
  found by actually driving the browser rather than reasoning about the code.
- Example 4's screenshots (chart dropping from 249 to 1 pod after `fly_to`) are the best
  single proof-point in the article that the chart and the chat are reading the *same*
  state; consider using the after-`fly_to` screenshot as the article's hero rather than
  the before shot (already done -- hero is `04_combined_after_flyto.webp`).
- Could cut for a shorter page: the "Installation" section's one-liner could merge into
  the intro paragraph; the `querychat.express` vs. plain `QueryChat` judgment call could
  move to a footnote rather than its own bullet, if space is tight.
- Not covered, and worth a future pass: streaming *tool* arguments as they're generated
  (chatlas's eager/fine-grained tool streaming), and a second provider (OpenAI via
  `chatlas.ChatOpenAI`) to confirm nothing here is Anthropic-specific -- the article
  claims this but only verifies against Anthropic.

## What was dropped from the old reports

Nothing: there is no prior `docs/widget-reports/` entry for this cross-cutting topic --
querychat/shinychat accessor-driven patterns postdate the old report pass entirely.

## Update 2026-11-11 (main @ 32ca7035)

shinywidgets: `0.8.2.post1.dev135+g32ca7035` (worktree detached at `main`, commit
`32ca7035`). Same dependency overlay as before: `querychat 0.9.0`, `chatlas 0.23.0`,
`anthropic 2.8.0` (unpinned `uv run --no-sync --with querychat --with chatlas --with
anthropic`; not shadowing anything in the locked venv). Model: `claude-haiku-5-5`
throughout, real API calls (`ANTHROPIC_API_KEY` was set in this environment for the
whole session; never printed or logged). Total cost for this update was a handful of
cents (7 real chat turns across the re-verification runs below).

**What changed and why**: #437 ("Accessor redesign: every accessor attaches at render
and retains its value across re-renders, plus `.read()`") removed the lazy-attach/
first-read behavior that example 2's `_warm_up_selected` effect and example 4's
`_warm_up_bounds` effect worked around. Every accessor now attaches the moment its
output renders and records interactions whether or not anything has read it yet, so
both warm-up effects are now dead code, and the finding in the old "Bugs found" section
below (event accessors attach lazily on first read) **no longer applies on current
main**. This was this article's whole point even before the redesign -- "read on
demand" is now the headline, unqualified capability rather than something that needs a
startup read to make safe.

- Removed `_warm_up_selected` (`@reactive.effect` reading `plot.selected()`
  unconditionally at startup) from `examples/02_selection_to_chat_context.py`, and the
  now-unused `from shiny import reactive` import that came with it.
- Removed `_warm_up_bounds` (same idiom, `map.bounds()`) from
  `examples/04_map_chart_chat_combined.py`. It was already commented "no longer
  required" (a prior pass had half-fixed it for state accessors only); now deleted
  outright, since the state/event split it referenced doesn't exist anymore.
- Rewrote the article's intro, section 2's lead-in code comment, section 2's closing
  paragraph, section 4's embedded code block and closing paragraph, and the "Where to go
  next" list to use the current terminology (kept/re-seeded, read on demand) and to stop
  describing a bug that no longer exists.
- Deleted the "Read an event accessor before the model's first use of it, or its first
  event is lost" pitfall from the **Pitfalls** section entirely, per the update brief's
  "delete, don't soften" instruction -- it described exactly the bug #437 fixed.
- `examples/01_querychat_to_widgets.py` and `examples/03_llm_tool_drives_map.py` needed
  no code changes (neither ever had a warm-up effect; neither accessor pattern they use
  was affected by the redesign's behavior, only by its terminology in the surrounding
  prose, which didn't reference either example).

**Re-verification table** (every file in `examples/`, this pass):

| File | Edited? | Ran in browser | Gesture | Real LLM call | Screenshot | Result |
|---|---|---|---|---|---|---|
| `01_querychat_to_widgets.py` | no | yes | typed querychat question via Playwright | yes | not replaced (unchanged behavior; see below) | same result as before: 2 Americas countries matched and highlighted |
| `02_selection_to_chat_context.py` | yes (warm-up removed) | yes, 3 consecutive full runs | real plotly lasso drag (Playwright mouse events), no prior accessor read anywhere in the app | yes (3 calls) | replaced (`02_selection_lasso.webp`, `02_selection_after.webp`) | **all 3/3 runs** correctly summarized the lasso selection with no warm-up -- see "Verification: read on demand, no warm-up" below |
| `03_llm_tool_drives_map.py` | no | yes | typed "fly to nairobi please" | yes | not replaced (unchanged behavior) | same result as before: map recentered on Nairobi, zoom 11 |
| `04_map_chart_chat_combined.py` | yes (warm-up removed) | yes, 2 consecutive full runs | typed "what's visible..." as the FIRST interaction (no pan/zoom, no prior accessor read), then "fly to the west island" | yes (4 calls across 2 runs) | replaced (`04_combined_before.webp`, `04_combined_after_flyto.webp`) | **both runs** correct on the first question, before any user gesture on the map at all |

Screenshots: Playwright Chromium, 1280x800 (900 tall for example 4), `device_scale_factor=2`,
launched with `--use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist`.
All four servers run one at a time on ports 8201-8204 from
`scratchpad/main-wt`, drivers in `scratchpad/agents/articles-a/drive_ex0{1,2,3,4}.py`
(not copied into the article; throwaway).

### Verification: read on demand, no warm-up

This is the finding the whole update turns on, so it got the most scrutiny:

- **Example 2** (lasso &rarr; chat): ran the full lasso-then-ask sequence 3 times in a row
  against the edited file (no warm-up effect present). All 3 runs correctly summarized
  the selection (9 countries each time, mean GDP ~$37,700, mean life expectancy ~79).
  The old NOTES (pre-#437) reported the *unfixed* version losing the selection in 2 of 3
  trials under the identical sequence; the fixed version now succeeds every time.
- **Example 4** (map + chart + chat): ran the "ask before touching the map at all" case
  twice. Both times, the very first chat message -- sent within ~2 seconds of page
  load, before any pan/zoom gesture -- got the correct count (249 pods, night/morning/
  afternoon/evening breakdown matching the bar chart exactly). This is a slightly
  stronger test than example 2's: `map.bounds()` cancels (no seeded value) until the
  browser's first viewport report, so this also confirms that report arrives fast
  enough in practice that a chat-driven app never has to wait for it.

### Bugs found (2026-11-11)

None new. The one bug this article reported previously (event accessors attach lazily
on first read, #437's whole subject) is now fixed on current `main`, confirmed by the
re-verification above. No other shinywidgets issues surfaced while re-reading
`shinywidgets/_render_widget.py`'s `clicked()`/`selected()`/`bounds()` docstrings or
driving the four apps.

### Judgment calls

- Left `01_querychat_to_widgets.py` and `03_llm_tool_drives_map.py`'s screenshots as
  they were (not retaken): their code didn't change and their behavior was re-confirmed
  identical (see table above), so retaking screenshots that would show the same thing
  seemed like churn rather than verification. Re-ran them anyway, in a real browser,
  because the update brief asked this article's examples to be re-verified broadly, not
  just the two that changed.
- The "9 countries" lasso in example 2's new screenshots is a different, smaller
  selection than the "28 countries" in the pre-update screenshots (a different
  Playwright driver drew a tighter box over the same wealthy-cluster region). This
  doesn't change anything about what the example teaches; the article's prose and quoted
  model answer were updated to match the new numbers so nothing describes a screenshot
  that isn't there.

### Editor's notes for the website

Unchanged from the prior pass (still accurate): example 2's screenshots remain the
strongest section, example 4's hero is still the best single proof that the chart and
chat read the same state. One addition: example 4's "before" screenshot now makes an
even stronger case for "read on demand" than before, since the chat response visible
there answers the user's very first message, with the map still at its construction-time
view.
