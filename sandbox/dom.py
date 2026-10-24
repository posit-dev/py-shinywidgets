from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width":1000,"height":700})
    pg.goto("http://127.0.0.1:19377")
    pg.wait_for_timeout(5000)
    loc = pg.locator("#atlas").get_by_text("c", exact=True)
    print(loc.count(), [l.evaluate("e=>e.outerHTML.slice(0,200)") for l in loc.all()])
    loc.last.click()
    pg.wait_for_timeout(1500)
    print(pg.inner_text("#selection_size"))
    pg.screenshot(path="sandbox/shot3.png")
    b.close()
