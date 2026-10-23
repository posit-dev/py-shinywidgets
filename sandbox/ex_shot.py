from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width":1400,"height":800})
    errs=[]
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type=="error" else None)
    pg.goto("http://127.0.0.1:19379")
    pg.wait_for_selector("#atlas .embedding-atlas-widget-container"); pg.wait_for_timeout(4000)
    print(pg.inner_text("#summary"))
    pg.locator("#atlas").get_by_text("chess", exact=True).last.click(); pg.wait_for_timeout(2000)
    print(pg.inner_text("#summary"))
    pg.screenshot(path="sandbox/ex.png"); print(errs); b.close()
