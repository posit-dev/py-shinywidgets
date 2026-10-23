from __future__ import annotations

import time

from playwright.sync_api import Page, expect


def test_rerender_timing(page: Page, local_app) -> None:
    msgs: list[str] = []
    page.on("console", lambda msg: msgs.append(f"{msg.type}: {msg.text}") if msg.type == "error" else None)
    page.goto(local_app.url)
    expect(page.locator("#fill_plot .ipyvolume-canvas-container")).to_have_count(1, timeout=30000)
    for i in range(1, 4):
        t0 = time.time()
        page.click("#rerender")
        t_click = time.time()
        page.wait_for_function(f"() => document.querySelector('#render_count').innerText === '{i}'", timeout=60000)
        t_count = time.time()
        page.wait_for_function("() => document.querySelectorAll('#fill_plot .ipyvolume-canvas-container').length === 1", timeout=60000)
        t_canvas = time.time()
        print(f"iter {i}: click={t_click-t0:.2f}s count={t_count-t0:.2f}s canvas={t_canvas-t0:.2f}s")
    print("ERRORS:", msgs)
