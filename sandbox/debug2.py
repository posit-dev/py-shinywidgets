import time
from pathlib import PurePath
from playwright.sync_api import sync_playwright
from shiny.run._run import shiny_app_gen
import sys
sys.path.insert(0, "tests/playwright")
from conftest import expose_manager

sa_gen = shiny_app_gen(PurePath("tests/playwright/render_ipycanvas/app.py"), env={})
app = next(sa_gen)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.route("**/output.js", expose_manager)
        page.on("console", lambda msg: print("CONSOLE", msg.type, msg.text[:200]) if msg.type == "error" else None)
        page.goto(app.url)
        time.sleep(6)
        print(page.evaluate("""async () => {
            const mgr = window.widgetManager;
            const out = [];
            for (const [id, p] of Object.entries(mgr._models)) {
                try {
                    const m = await p;
                    out.push(id.slice(0,8) + ' ' + m.get('_model_name') + (m.get('_model_name') === 'CanvasManagerModel' ? ' currentCanvas=' + (m.currentCanvas ? 'SET' : String(m.currentCanvas)) : ''));
                } catch (e) {
                    out.push(id.slice(0,8) + ' ERR ' + String(e).slice(0,80));
                }
            }
            return out.join('\\n');
        }"""))
        browser.close()
finally:
    pass
