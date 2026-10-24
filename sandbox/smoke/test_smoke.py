from __future__ import annotations

from playwright.sync_api import Page


def test_ipyvolume_smoke(page: Page, local_app) -> None:
    errors: list[str] = []
    failed: list[str] = []
    msgs: list[str] = []
    page.on("console", lambda msg: (errors.append(msg.text) if msg.type == "error" else msgs.append(f"{msg.type}: {msg.text}")))
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.on("response", lambda res: failed.append(f"{res.status} {res.url}") if res.status >= 400 else None)
    page.goto(local_app.url)
    try:
        page.wait_for_selector("#fig canvas", timeout=20000)
        print("CANVAS APPEARED")
    except Exception as e:
        print("NO CANVAS:", type(e).__name__)
    page.wait_for_timeout(2000)
    html = page.evaluate("() => document.querySelector('#fig').innerHTML.slice(0, 500)")
    print("FIG HTML:", html)
    print("ERRORS:", errors)
    print("FAILED:", failed)
    print("CONSOLE:", msgs[:40])
