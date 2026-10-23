import subprocess, sys, time
from playwright.sync_api import sync_playwright
proc = subprocess.Popen([sys.executable, "-m", "shiny", "run", "examples/mosaic_widget/app.py", "--port", "48932"])
time.sleep(6)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width":1300,"height":800})
        errs=[]
        pg.on("console", lambda m: errs.append(m.text) if m.type=="error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://localhost:48932"); pg.wait_for_selector("#dashboard svg circle", timeout=30000)
        box = pg.locator("#dashboard .plot svg").first.bounding_box()
        pg.mouse.move(box["x"]+200, box["y"]+100); pg.mouse.down(); pg.mouse.move(box["x"]+350, box["y"]+200, steps=8); pg.mouse.up()
        time.sleep(2)
        print(pg.locator("#n_selected").inner_text(), errs)
        pg.screenshot(path="sandbox/example.png")
finally:
    proc.terminate()
