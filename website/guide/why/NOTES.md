# NOTES: Overview

## Update 2026-11-12: page replaced

The Overview page was replaced by "Why shinywidgets?" (this directory, renamed from `overview/`). Everything
below describes the old Overview page; the new page's examples (`examples/reactive.py`) were run in a browser
and its screenshot re-shot when written.

## Versions

- shinywidgets: worktree `site-content-gaps` @ `943183cd` (branch `docs/site-content-gaps`), shiny 1.9.0,
  plotly 6.9.0. Date: 2026-11-11.

## Verification table

This page has no examples of its own (per the task block: "No examples"). Its only verifiable content is
links and embedded images, all of which point into other guides'/articles' existing, already-verified
assets.

| Check | Result |
|---|---|
| `check_docs.py --links` | clean except the forward link to `../installation/article.md`, which resolves once Task 4 lands (same agent, next). `../updating-in-place/article.md` already resolved: Task 5 had landed in this worktree by the time this ran. |
| Every image referenced | opened and looked at (see "Judgment calls" below for which 8 were picked and why). |

## Judgment calls

- **"the existing `*/img/hero.webp`" (task block) read as "each guide's declared hero image", not the
  literal filename.** Several widget groups (Tables & grids, Data exploration, Networks) have *no* guide
  whose hero image is literally named `hero.webp` -- their guides declare a `hero:` front-matter value
  pointing elsewhere (e.g. itables' hero is `img/gallery_showcase_gapminder_dashboard_after.webp`). Reading
  the task block literally would leave 3 of 8 groups with no picture at all, which can't be the intent of "a
  visual tour of one hero screenshot per widget group" covering all groups. I used each picked guide's
  `hero:` front-matter value instead. Flagging in case the maintainer wants it read more literally (which
  would mean dropping the Tables & grids / Data exploration / Networks pictures, or picking a different,
  non-hero screenshot for those three).
- **Picked widgets per group** (one each, chosen for a visually clear, compelling still at thumbnail size,
  and viewed before referencing): plotly (Charts), itables (Tables & grids), mosaic (Data exploration),
  lonboard (Maps & geospatial), k3d (3D -- picked over pythreejs, whose `hero.webp` is a plain red cube with
  no data in it), nglview (Scientific), ipycytoscape (Networks), drawdata (Input & drawing).
- `hero:` front matter points at `../../plotly/img/hero.webp` (not a locally-owned file) since this page's
  own `img/` is empty by design (no examples, and the task says to link image paths rather than copy them).
  This directory has no files in it; consistent with the no-examples instruction, not an oversight.

## Editor's notes for the website

- The "visual tour" section is the strongest part of the page and the one most worth getting right visually
  on the actual site (an 8-up image grid, not the sequential list markdown forces here).
- Kept the opening paragraph to two short paragraphs; cut a draft third paragraph that started listing
  specific widget names, since "A visual tour" does that job better.
