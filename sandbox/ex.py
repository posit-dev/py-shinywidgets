from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1100,"height":700})
    errs=[]
    pg.on("console", lambda m: errs.append(m.text) if m.type=="error" else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:18316"); pg.wait_for_selector("#structure canvas", timeout=30000); pg.wait_for_timeout(5000)
    pg.screenshot(path="sandbox/ex1.png")
    pg.select_option("#representation","licorice"); pg.wait_for_timeout(5000)
    pg.screenshot(path="sandbox/ex2.png")
    pg.locator("#structure canvas").click(position={"x":370,"y":330}); pg.wait_for_timeout(2000)
    print(errs, pg.locator("#picked_atom").inner_text())
