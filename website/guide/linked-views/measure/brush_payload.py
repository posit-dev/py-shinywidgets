"""Measure real websocket bytes (and optionally latency) per brush step.

Usage:
    uv run --no-sync python docs/widget-guides/articles/linked-views/measure/brush_payload.py \
        APP --scale N [--timing]

`APP` is one of the three apps in `../examples/`: `18_datashader_brush_summaries.py`,
`19_scattergl_lasso_raw_points.py`, or `20_mosaic_brush_in_widget.py`. `--scale` sets
the `LINKED_VIEWS_ROWS` environment variable, which 18 and 19 read to control how many
Gaia rows they load (20 always runs at the full 5,000,000-row scale and ignores it).

Starts the app, loads it in headless Chromium, and records every websocket frame's
byte size and direction (`page.on("websocket")` + `framesent`/`framereceived`), minus
Shiny's own per-flush protocol chatter (`{"busy": ...}`, the empty input-sync message,
comm-open acks) -- generic session bookkeeping that happens on every reactive flush
regardless of what changed, not part of any widget's payload.

Frames up through the first render, plus one full warm-up drag and a settle pause, are
discarded: the first load pays for the JS bundle and the initial image/figure, and
holoviews/bokeh's comm channel in particular has noticeable one-time setup cost on the
first-ever interaction that the warm-up exists to absorb. The measured drag is 20
steps, one `mouse.move` per step, 50ms apart (1 second total), inside a single
mouse-down..mouse-up gesture appropriate to the app (a histogram box-select for 18/20,
a lasso for 19).

18's and 20's accessors debounce at 250ms, so a 1-second drag produces on the order of
4 real network emissions, not 20 -- bucketing frames to individual mouse-move indices
would mostly report zero. Instead this script reports TOTAL bytes transferred during
the whole measured gesture in each direction, plus that total divided by the 20 nominal
steps as a simple average -- directly comparable between scales and apps, which is what
the article's claim (flat vs. growing with N) is actually about.

With `--timing`, each step's wall-clock `mouse.move` time is also compared against the
next DOM mutation observed on that app's "linked output" (a `MutationObserver` attached
before the drag starts), and the script additionally reports median end-to-end latency
per step. Timing numbers are not collected by Task 6 (the article leaves its latency
column pending) -- this flag exists for the dedicated timing wave to reuse this same
script.

`--timing` fixes (Task 11): the smoke check this script shipped with recorded zero
MutationObserver events for every app, from two independent bugs.

1. Every app's gesture is a deterministic function of the plot's own bounding box, so
   the warm-up drag and the measured drag used to trace the *exact same path* and
   settle on the *exact same* final brushed region. The MutationObserver was attached
   right after the warm-up, by which point the linked output already showed that
   region's values -- so the measured drag (retracing the identical path) produced the
   identical values at every step and the observed element never actually changed,
   regardless of how much network traffic the debounced accessor sent (confirmed
   directly: `page.eval_on_selector_all` diffs of the rendered bar/table DOM showed
   real changes during warm-up and zero changes during the "measured" replay). Fixed
   by running a *decoy* gesture -- a different region (`decoy_18`/`decoy_19`/
   `decoy_20`) -- after the warm-up, only in `--timing` mode. This leaves the linked
   output settled on a region the real, measured gesture's steps will genuinely differ
   from at every point, without changing the warm-up/measured gesture pair the
   bytes-only (no `--timing`) path already used and that Task 6's committed numbers
   were measured with.
   The observer is attached *before* the decoy drag runs, not right before the
   measured drag: a `page.evaluate()` call (attaching the observer, or even a no-op
   `page.evaluate("() => 1")`) placed immediately ahead of the measured drag was
   observed to silently suppress that drag's own server round trip entirely (reduced
   a ~2.1 MB received payload to ~2 KB, reproducibly) -- a Playwright/CDP-level
   interaction with the mouse-event sequence that follows, not a shinywidgets bug.
   Attaching the observer earlier (right after warm-up, before the decoy) avoids the
   interaction; any mutation the decoy drag itself causes is then timestamped well
   before the measured drag's first `mouse.move`, so `latency_per_step`'s per-step
   time windows (each anchored to a *measured*-drag move time) naturally exclude it.
2. App 20's watch selector, `svg[class^='plot-']:nth-of-type(3)`, never matched
   anything: Mosaic/vgplot gives all three marks (raster, mag hist, plx hist) the
   *same* generated class, and they sit under different parent `<div>`s from the
   vconcat/hconcat layout, so each is the first (not third) svg-type child of its own
   parent -- `:nth-of-type` counts per-parent, per-tag-name, not across a class
   selector's matches. Separately, even a corrected by-index selector
   (`querySelectorAll(...)[2]`) isn't reliable here: watching it directly showed
   Mosaic replaces a mark's whole `<svg>` subtree (new DOM nodes) on every crossfilter
   update rather than mutating it in place, which detaches a previously-observed node
   from the live tree with no mutation record. Fixed by watching the stable output
   wrapper `#dashboard` (the div shinywidgets itself owns and never replaces) instead
   of a specific mark's svg.
"""

from __future__ import annotations

import argparse
import math
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, List, Tuple

from playwright.sync_api import Page, sync_playwright

TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))
import smoke  # noqa: E402  (path must be extended first)

WAIT_SELECTOR = smoke.DEFAULT_WAIT_SELECTOR
WAIT_TIMEOUT_SECONDS = smoke.WAIT_TIMEOUT_SECONDS
STEP_MS = 50
N_STEPS = 20
WARMUP_SETTLE_SECONDS = 3.0
MEASURED_SETTLE_SECONDS = 2.0

# Shiny/shinywidgets session bookkeeping that fires on every reactive flush
# regardless of what changed -- not part of any widget's own payload.
NOISE_PREFIXES = ('{"busy"', '{"values": {}, "inputMessages"')
NOISE_MARKERS = ("shinywidgets_comm_ack",)

Point = Tuple[float, float]
Frame = Tuple[float, str]  # (wall-clock time, raw text payload)
RectJS = "els => els.map(e => { const r = e.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; })"


def gesture_18(page: Page, *, lo_frac: float = 0.3, hi_frac: float = 0.8) -> Tuple[Point, List[Point]]:
    # Box-select across the magnitude histogram (the first of the two plotly
    # bar charts): a left-to-right drag inside its drag layer.
    rect = page.eval_on_selector_all(".plotly .nsewdrag", RectJS)[0]
    x0, x1 = rect["x"] + rect["w"] * lo_frac, rect["x"] + rect["w"] * hi_frac
    y = rect["y"] + rect["h"] * 0.5
    steps = [(x0 + (x1 - x0) * i / N_STEPS, y) for i in range(1, N_STEPS + 1)]
    return (x0, y), steps


def decoy_18(page: Page) -> Tuple[Point, List[Point]]:
    # A different magnitude range than gesture_18's own 0.3-0.8 span, so a
    # `--timing` run's pre-observer "settle" state differs from every point
    # the real, measured drag will pass through (see decoy rationale above
    # `attach_mutation_observer`).
    return gesture_18(page, lo_frac=0.05, hi_frac=0.2)


def gesture_19(page: Page, *, cx_frac: float = 0.45, cy_frac: float = 0.5) -> Tuple[Point, List[Point]]:
    # Lasso a roughly elliptical region of the scatter: 20 points around an
    # ellipse, closing back near the start on mouse-up.
    rect = page.eval_on_selector_all(".plotly .nsewdrag", RectJS)[0]
    cx, cy = rect["x"] + rect["w"] * cx_frac, rect["y"] + rect["h"] * cy_frac
    rx, ry = rect["w"] * 0.12, rect["h"] * 0.12
    start = (cx + rx, cy)
    steps = [
        (cx + rx * math.cos(2 * math.pi * i / N_STEPS), cy + ry * math.sin(2 * math.pi * i / N_STEPS))
        for i in range(1, N_STEPS + 1)
    ]
    return start, steps


def decoy_19(page: Page) -> Tuple[Point, List[Point]]:
    # A different ellipse center, so the lasso's pre-observer "settle" set of
    # selected points is almost certainly disjoint from the real one.
    return gesture_19(page, cx_frac=0.15, cy_frac=0.2)


def gesture_20(page: Page, *, lo_offset: float = 80, hi_offset: float = 250) -> Tuple[Point, List[Point]]:
    # intervalX drag across the magnitude histogram's brush overlay (the
    # second of the three `svg.plot-*` elements: raster, mag hist, plx hist).
    svg = page.eval_on_selector_all("svg[class^='plot-']", RectJS)[1]
    x0, x1 = svg["x"] + lo_offset, svg["x"] + hi_offset
    y = svg["y"] + 100
    steps = [(x0 + (x1 - x0) * i / N_STEPS, y) for i in range(1, N_STEPS + 1)]
    return (x0, y), steps


def decoy_20(page: Page) -> Tuple[Point, List[Point]]:
    # A different x-range than gesture_20's own 80-250px span.
    return gesture_20(page, lo_offset=300, hi_offset=340)


# Each app's gesture function, its decoy (a different region, used only by
# `--timing` -- see the module docstring's "--timing fixes"), and the output
# element whose DOM mutations `--timing` watches as "the linked output" the
# brush drives.
#
# App 20 watches the whole widget's output wrapper (`#dashboard`, shinywidgets'
# own, stable mount point), not one mark's `<svg>`: Mosaic/vgplot replaces a
# mark's entire svg subtree with new DOM nodes on every crossfilter update
# instead of mutating it in place, so a MutationObserver on a specific mark's
# (previously-observed) svg node goes silent the moment that node is replaced.
APPS: dict[str, Tuple[Callable[[Page], Tuple[Point, List[Point]]], Callable[[Page], Tuple[Point, List[Point]]], str]] = {
    "18_datashader_brush_summaries": (gesture_18, decoy_18, "#plx_hist"),
    "19_scattergl_lasso_raw_points": (gesture_19, decoy_19, "#table"),
    "20_mosaic_brush_in_widget": (gesture_20, decoy_20, "#dashboard"),
}


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("app", type=Path, help="path to one of the apps in ../examples/")
    parser.add_argument("--scale", type=int, required=True, help="rows to load (LINKED_VIEWS_ROWS)")
    parser.add_argument("--timing", action="store_true", help="also measure end-to-end latency per step")
    args = parser.parse_args(argv)

    stem = args.app.stem
    if stem not in APPS:
        parser.error(f"unknown app {stem!r}; expected one of {sorted(APPS)}")
    gesture_fn, decoy_fn, watch_selector = APPS[stem]

    return run(args.app, args.scale, gesture_fn, decoy_fn, watch_selector, args.timing)


def run(
    app: Path,
    scale: int,
    gesture_fn: Callable[[Page], Tuple[Point, List[Point]]],
    decoy_fn: Callable[[Page], Tuple[Point, List[Point]]],
    watch_selector: str,
    timing: bool,
) -> int:
    env = {**os.environ, "LINKED_VIEWS_ROWS": str(scale), "PYTHONUNBUFFERED": "1"}
    log_path = Path.cwd() / f".brush_payload_{app.stem}_{scale}.log"
    server = subprocess.Popen(
        [sys.executable, "-m", "shiny", "run", str(app), "--port", "0", "--host", "127.0.0.1"],
        stdout=open(log_path, "wb"),
        stderr=subprocess.STDOUT,
        env=env,
    )
    try:
        port = wait_for_port(server, log_path)
        if port is None:
            print(f"server never started:\n{smoke.read_log(log_path)}")
            return 1

        sent: List[Frame] = []
        recv: List[Frame] = []

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(device_scale_factor=2)
                page.on(
                    "websocket",
                    lambda ws: (
                        ws.on("framesent", lambda payload: sent.append((time.time(), as_text(payload)))),
                        ws.on("framereceived", lambda payload: recv.append((time.time(), as_text(payload)))),
                    ),
                )
                page.goto(f"http://127.0.0.1:{port}/")
                page.wait_for_selector(WAIT_SELECTOR, timeout=int(WAIT_TIMEOUT_SECONDS * 1000))
                time.sleep(1.5)  # let the first render's trailing frames land

                # Warm-up drag: absorb one-time setup cost (accessor binding,
                # first filter/crossfilter query plan, the first-ever
                # holoviews/bokeh comm round trip -- all observed to be
                # noticeably more expensive than steady-state), then discard
                # every frame recorded so far.
                drag(page, gesture_fn)
                time.sleep(WARMUP_SETTLE_SECONDS)

                if timing:
                    # Attach the observer now, before the decoy drag below --
                    # not right before the measured drag. A `page.evaluate()`
                    # call (this one, or even a no-op) immediately before the
                    # measured drag was observed to silently suppress that
                    # drag's own server round trip (reproduced with a trivial
                    # `page.evaluate("() => 1")` in its place -- a Playwright/
                    # CDP-level timing interaction with the following mouse
                    # sequence, not a shinywidgets bug). Attaching here instead
                    # means any mutation the decoy drag itself causes is
                    # timestamped well before the measured drag's first
                    # `mouse.move`, so `latency_per_step`'s per-step time
                    # windows (each anchored to a measured-drag move time)
                    # naturally exclude it without any extra bookkeeping.
                    attach_mutation_observer(page, watch_selector)

                    # Decoy drag: settle the linked output on a region the
                    # measured drag (identical path every time, since
                    # gesture_fn is a deterministic function of the plot's
                    # bounding box) doesn't pass through. Without this, the
                    # measured drag retraces the warm-up drag's exact path and
                    # the observed element never actually changes (see the
                    # module docstring's "--timing fix" note), even though
                    # real network traffic is still sent.
                    drag(page, decoy_fn)
                    time.sleep(WARMUP_SETTLE_SECONDS)

                sent.clear()
                recv.clear()

                move_times = drag(page, gesture_fn)
                time.sleep(MEASURED_SETTLE_SECONDS)  # drain trailing/debounced frames

                sent_total, sent_n = summarize(sent)
                recv_total, recv_n = summarize(recv)
                print(f"app={app.name} scale={scale:,}")
                print(
                    f"  browser-to-server: {sent_total:,} bytes total over {sent_n} frames "
                    f"({sent_total / N_STEPS:,.0f} bytes/step avg over {N_STEPS} nominal steps)"
                )
                print(
                    f"  server-to-browser: {recv_total:,} bytes total over {recv_n} frames "
                    f"({recv_total / N_STEPS:,.0f} bytes/step avg over {N_STEPS} nominal steps)"
                )

                if timing:
                    mutation_times = read_mutations(page)
                    latencies = latency_per_step(move_times, mutation_times)
                    median_ms = statistics.median(latencies) if latencies else float("nan")
                    print(f"  latency: median {median_ms:.0f} ms/step over {len(latencies)} observed steps  {[round(v) for v in latencies]}")
            finally:
                browser.close()
    finally:
        smoke.stop_server(server)
        log_path.unlink(missing_ok=True)

    return 0


def wait_for_port(server: "subprocess.Popen[bytes]", log_path: Path) -> int | None:
    deadline = time.monotonic() + WAIT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if server.poll() is not None:
            return None
        port = smoke.find_port(smoke.read_log(log_path))
        if port is not None:
            return port
        time.sleep(0.2)
    return None


def as_text(payload: object) -> str:
    if isinstance(payload, (bytes, bytearray)):
        return payload.decode("utf-8", errors="replace")
    return str(payload)


def is_noise(text: str) -> bool:
    if any(text.startswith(p) for p in NOISE_PREFIXES):
        return True
    return any(m in text for m in NOISE_MARKERS)


def summarize(frames: List[Frame]) -> Tuple[int, int]:
    kept = [text for _, text in frames if not is_noise(text)]
    total_bytes = sum(len(text.encode("utf-8")) for text in kept)
    return total_bytes, len(kept)


def drag(page: Page, gesture_fn: Callable[[Page], Tuple[Point, List[Point]]]) -> List[float]:
    start, steps = gesture_fn(page)
    page.mouse.move(*start)
    page.mouse.down()
    move_times: List[float] = []
    for point in steps:
        move_times.append(time.time())
        page.mouse.move(*point)
        time.sleep(STEP_MS / 1000)
    page.mouse.up()
    return move_times


def attach_mutation_observer(page: Page, selector: str) -> None:
    page.evaluate(
        """(selector) => {
            window.__brushMutations = [];
            const target = document.querySelector(selector);
            if (!target) return;
            const obs = new MutationObserver(() => {
                window.__brushMutations.push(performance.now());
            });
            obs.observe(target, {attributes: true, childList: true, subtree: true, characterData: true});
            window.__brushObserver = obs;
        }""",
        selector,
    )


def read_mutations(page: Page) -> List[float]:
    # performance.now() is ms since navigation start; add performance.timeOrigin
    # (epoch ms) to land on the same wall clock as Python's time.time().
    origin, times = page.evaluate(
        "() => [performance.timeOrigin, (window.__brushMutations || []).splice(0)]"
    )
    return [(origin + t) / 1000 for t in times]


def latency_per_step(move_times: List[float], mutation_wall_times: List[float]) -> List[float]:
    latencies: List[float] = []
    for i, move_t in enumerate(move_times):
        window_end = move_times[i + 1] if i + 1 < len(move_times) else move_t + 1.0
        after = [m for m in mutation_wall_times if move_t <= m < window_end]
        if after:
            latencies.append((after[0] - move_t) * 1000)
    return latencies


if __name__ == "__main__":
    sys.exit(main())
