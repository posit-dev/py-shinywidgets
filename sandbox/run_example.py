import time
from pathlib import PurePath
from playwright.sync_api import sync_playwright
from shiny.run._run import shiny_app_gen

sa_gen = shiny_app_gen(PurePath("examples/ipycanvas/app.py"), env={})
app = next(sa_gen)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)[:200]))
        page.on("console", lambda msg: errors.append(msg.text[:200]) if msg.type == "error" else None)
        page.goto(app.url)
        page.wait_for_selector("#draw canvas", timeout=30000)
        page.wait_for_selector("#anim canvas", timeout=30000)
        # draw a stroke
        box = page.locator("#draw canvas").bounding_box()
        page.mouse.move(box["x"]+50, box["y"]+50)
        page.mouse.down()
        page.mouse.move(box["x"]+150, box["y"]+120, steps=5)
        page.mouse.up()
        # start animation
        page.click("#toggle")
        time.sleep(1.5)
        # verify pixels on both canvases
        import sys
        sys.path.insert(0, "tests/playwright")
        from conftest import CANVAS_HAS_PIXELS_JS
        print("draw has pixels:", page.evaluate(CANVAS_HAS_PIXELS_JS, "#draw"))
        print("anim has pixels:", page.evaluate(CANVAS_HAS_PIXELS_JS, "#anim"))
        print("errors:", errors[:5])
        browser.close()
finally:
    pass
