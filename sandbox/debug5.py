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
        page.on("request", lambda req: print("REQ", req.url) if "ipycanvas" in req.url else None)
        page.goto(app.url)
        time.sleep(4)
        browser.close()
finally:
    pass
