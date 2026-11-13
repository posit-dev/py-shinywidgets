# NOTES: trading-desk

- Promoted from `docs/widget-guides/perspective/gallery/showcase_trading_desk.py`,
  unchanged except the `# Run:` header line.
- Re-verified 2026-11-02 in `main-wt`: perspective-python 5.6.1, already in the shared venv.
  No `--with` overlay needed.
- The streaming effect's `tick.set(tick.get() + 1)` inside `reactive.isolate()`, gated on
  `input.live()` and paired with `reactive.invalidate_later(0.5)`, is a deliberate animation
  tick (the same pattern used by the perspective guide's own `template_live_feed.py`), not
  the unguarded self-triggering effect the review-pass TODO warns about -- it is both gated
  and isolated.

## Verification table

| Gesture | Driven | Server-state confirmed |
|---|---|---|
| Load + both viewers render | yes (Playwright) | grid and treemap visible, `img/hero.webp` |
| Wait ~2.5s with streaming on | yes (passive) | `#n_trades` changed from `680 / 680` to `880 / 880`, confirming the table genuinely grows |
| Click the "Pivot" radio | yes | left viewer regrouped by sector/symbol/side with bar-mode notional/P&L coloring, right viewer's treemap labels changed, `img/after_pivot.webp` |

Did not separately re-verify the `view_config()`-driven value boxes responding to a
browser-set filter (opening the grid's settings panel and typing a filter) in this pass; the
perspective guide's own verification already covers `view_config()`'s filter round trip, and
the streaming + preset-switch gestures above exercise the showcase's two other headline
mechanisms.

## Judgment calls

- None beyond the header-line edit.
