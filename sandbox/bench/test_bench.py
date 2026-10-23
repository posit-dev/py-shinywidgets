from __future__ import annotations

import os
import time

from playwright.sync_api import Page, expect
from tests.playwright.conftest import wait_for_red_pixels


def test_bench(page: Page, local_app) -> None:
    n = os.environ.get("N", "10000")
    t0 = time.time()
    page.goto(local_app.url)
    expect(page.locator("#plot .ipyvolume-canvas-container")).to_have_count(1, timeout=60000)
    t1 = time.time()
    wait_for_red_pixels(page, "#plot canvas", timeout_ms=120000)
    t2 = time.time()
    print(f"BENCH n={n}: canvas_container={t1-t0:.2f}s first_frame={t2-t0:.2f}s")
