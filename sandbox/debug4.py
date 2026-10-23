import time
from pathlib import PurePath
from playwright.sync_api import sync_playwright
from shiny.run._run import shiny_app_gen

sa_gen = shiny_app_gen(PurePath("tests/playwright/render_ipycanvas/app.py"), env={})
app = next(sa_gen)

def patch_ipycanvas(route):
    print("ROUTE HIT", route.request.url)
    try:
        response = route.fetch()
        text = response.text()
        orig = "async switchCanvas(t){this.currentCanvas=await(0,a.unpack_models)(t,this.widget_manager)}"
        print("orig found:", orig in text)
        new = ("async switchCanvas(t){console.log('SWITCHCANVAS', t);"
               "try{this.currentCanvas=await(0,a.unpack_models)(t,this.widget_manager);"
               "console.log('SWITCHCANVAS resolved', !!this.currentCanvas)}"
               "catch(e){console.log('SWITCHCANVAS failed', String(e)); throw e}}")
        route.fulfill(response=response, body=text.replace(orig, new))
    except Exception as e:
        print("ROUTE ERROR", repr(e)[:200])
        try:
            route.continue_()
        except Exception:
            pass

try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.route("**/lib/ipycanvas-0.14/index.js", patch_ipycanvas)
        page.on("console", lambda msg: print("CONSOLE", msg.type, msg.text[:250]) if ("SWITCH" in msg.text or msg.type == "error") else None)
        page.on("pageerror", lambda err: None)
        page.goto(app.url)
        time.sleep(4)
        browser.close()
finally:
    pass
