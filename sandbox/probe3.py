from playwright.sync_api import sync_playwright
P=open('sandbox/port').read().strip()
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width":1100,"height":700})
    pg.on("pageerror", lambda e: print("PAGEERR", e))
    pg.on("console", lambda m: print("ERR", m.text[:200]) if m.type=="error" else None)
    pg.goto(f"http://localhost:{P}")
    pg.wait_for_selector("#scene canvas", timeout=60000); pg.wait_for_timeout(2500)
    print(pg.locator("#camera").inner_text())
    pg.evaluate("Shiny.setInputValue('point_size', 0.15)"); pg.wait_for_timeout(2000)
    print(pg.locator("#scene canvas").count(), pg.locator("#camera").inner_text())
    pg.screenshot(path="sandbox/ex.png"); b.close()
