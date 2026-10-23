from playwright.sync_api import sync_playwright
J="""()=>{const r=e=>{const b=e.getBoundingClientRect();return [b.width,b.height]};return {output:r(document.querySelector('#atlas')),atlas:r(document.querySelector('#atlas .embedding-atlas-widget-container')),body:r(document.querySelector('.card-body'))}}"""
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width":900,"height":700})
    pg.goto("http://127.0.0.1:19377")
    pg.wait_for_selector("#atlas .embedding-atlas-widget-container"); pg.wait_for_timeout(2000)
    print("900x700", pg.evaluate(J))
    pg.set_viewport_size({"width":700,"height":520}); pg.wait_for_timeout(1000)
    print("700x520", pg.evaluate(J))
    b.close()
