import time
from pathlib import PurePath
from playwright.sync_api import sync_playwright
from shiny.run._run import shiny_app_gen

sa_gen = shiny_app_gen(PurePath("tests/playwright/render_ipycanvas/app.py"), env={})
app = next(sa_gen)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.on("console", lambda msg: print("CONSOLE", msg.type, msg.text[:300]))
        seen=set()
        def on_err(err):
            k=str(err)[:60]
            if k in seen: return
            seen.add(k)
            print("PAGEERROR", str(err)[:200])
            print("STACK", (err.stack or "")[:1500])
        page.on("pageerror", on_err)
        page.on("response", lambda res: print("HTTP", res.status, res.url[-80:]) if res.status >= 400 else None)
        page.goto(app.url)
        time.sleep(8)
        print("DOM:", page.evaluate("() => document.querySelector('#canvas') && document.querySelector('#canvas').innerHTML.slice(0, 500)"))
        browser.close()
finally:
    app.stop()
