import time
from pathlib import PurePath
from playwright.sync_api import sync_playwright
from shiny.run._run import shiny_app_gen

sa_gen = shiny_app_gen(PurePath("tests/playwright/render_ipycanvas/app.py"), env={})
app = next(sa_gen)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 900, "height": 1200})
        page.goto(app.url)
        page.wait_for_selector("#canvas canvas", timeout=30000)
        time.sleep(3)
        print(page.evaluate("""() => {
          const el = document.querySelector('#canvas');
          const card = el.closest('.card');
          const body = el.closest('.card-body');
          const r = (e) => e ? Math.round(e.getBoundingClientRect().height) : null;
          const cls = (e) => e ? e.className : null;
          return JSON.stringify({
            cardH: r(card), bodyH: r(body), outH: r(el),
            outCls: cls(el), bodyCls: cls(body),
            bodyDisplay: getComputedStyle(body).display,
            cardStyle: card.getAttribute('style'), cardOuter: card.outerHTML.slice(0,200),
            outStyle: el.getAttribute('style'),
            canvasH: r(el.querySelector('canvas')),
            lmH: r(el.querySelector('.lm-Widget')),
          });
        }"""))
        browser.close()
finally:
    pass
