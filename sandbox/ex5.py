from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":900,"height":600})
    pg.goto("http://127.0.0.1:18317"); pg.wait_for_selector("#s canvas", timeout=30000); pg.wait_for_timeout(5000)
    pg.click("#go"); pg.wait_for_timeout(3000); pg.screenshot(path="sandbox/e5a.png")
    pg.click("#bg"); pg.wait_for_timeout(3000); pg.screenshot(path="sandbox/e5b.png")
