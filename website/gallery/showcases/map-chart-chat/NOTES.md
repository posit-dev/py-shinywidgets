# NOTES: map-chart-chat

- Promoted from
  `docs/widget-guides/articles/ai-exploration/examples/04_map_chart_chat_combined.py`,
  flagged by the coordinator as a strong showcase candidate mid-task (the AI-exploration
  article landed after this task started). Only change from the article's version: added a
  `#`-comment title line and a `# Run:` header line pointing at this directory's own `app.py`
  (the article's examples don't carry per-file run headers the way gallery apps do). The
  app body, including the `_warm_up_bounds` effect, is unchanged.
- This fills the "coordinate different widget libraries" + "AI exploration" breadth gaps:
  it is the only showcase in this bucket that pairs a map, a chart, *and* an LLM chat, with
  all three reading one shared accessor.

## Versions

- 2026-11-02, same `main-wt` worktree as the rest of this batch (commit `00f90249`), shiny
  1.9.0, ipyleaflet 0.20.0, plotly 6.9.0, shinychat 0.7.2 (already in the locked venv).
- chatlas and anthropic are NOT in the locked venv; installed as ephemeral
  `--with chatlas --with anthropic` overlays (unpinned, per the ai-exploration article's own
  NOTES.md, which confirmed the resolved versions -- chatlas 0.23.0, anthropic 2.3.0 -- match
  what it used).
- Real LLM calls throughout, via `chatlas.ChatAnthropic(model="claude-haiku-5-5")` and the
  `ANTHROPIC_API_KEY` already set in this environment. Two chat turns were made for this
  showcase's own re-verification (on top of the four the article already ran), well under
  the article's reported total cost.

## Verification table

| Gesture | Driven | Server-state confirmed |
|---|---|---|
| Load + map renders | yes (Playwright, swiftshader WebGL flags) | `#map .leaflet-container` visible, `img/hero.webp` |
| Chat: "what's visible on the map right now?" | yes (`shinychat.playwright.ChatController`) | reply's per-period counts match the chart's bars (127/38/33/51 of 249) |
| Chat: "fly to the west island" | yes | map recentered (visible marker moved in `img/after_fly_to.webp`), chart dropped to one "evening" bar, reply text consistent with both |

Driver script: `/private/tmp/.../scratchpad/agents/gallery-showcases/drive_chat.py` (scratch,
not copied into the repo).

## Update 2026-11-11 (main @ 32ca7035)

- **Removed the warm-up effect** (`_warm_up_bounds`). Since #437, every accessor attaches its
  browser-side listener at render and records interactions whether or not anything has read it
  yet -- there's no more lazy-attach-on-first-read behavior for the warm-up to work around.
  Rewrote the README's "A gotcha this showcase avoids" section into "Read on demand", describing
  the new guarantee instead of a gotcha that no longer exists.
- Verified with Playwright + `shinychat.playwright.ChatController` (`--with chatlas --with
  anthropic`, real `claude-haiku-5-5` calls): asked *"what's visible on the map right now?"* as
  the very first interaction (no prior pan/zoom, no prior chat turn) -- the exact scenario the
  warm-up effect existed for. `summarize_view` succeeded and returned counts (127/38/33/51 of
  249) matching the bar chart, confirming `map.bounds()` is live from first read with no warm-up.
  Server log had zero tracebacks. Note: `map.bounds()` itself still cancels (`req(False)`) until
  ipyleaflet's *own* first viewport report reaches the browser -- a real map-load race,
  independent of accessor attach timing -- so a tool call made in the first ~1-2s after page load
  (before the test gave the map 4s to settle) can still hit a `SilentException` inside the tool;
  this is expected and matches `ipyleaflet.bounds()`'s documented "cancels" behavior, not a
  regression from removing the warm-up.
- Accessors: `map.bounds()` -- re-verified with a real gesture (chat tool call with no prior
  read), confirmed against the chart's server-rendered counts.

## Judgment calls

- Added this as a 13th showcase (brief's target was ~8-12); kept it because it is the only
  three-way cross-library pairing (map + chart + chat) in the bucket and the coordinator
  explicitly flagged it. If the maintainer wants to stay at 12, this is the one I'd cut
  first since its underlying accessor pattern (`map.bounds()` -> chart) is already
  demonstrated without the chat in the `map-viewport-to-chart` *template*.
- Did not re-verify the `summarize_view`/`fly_to` allow-list rejection path (tested in the
  article's own example 3, not duplicated here) since this showcase's purpose is the
  three-way agreement, not the tool's input validation.
