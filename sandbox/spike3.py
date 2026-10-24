import subprocess, time, sys, json
from playwright.sync_api import sync_playwright
PORT=int(sys.argv[1])
p = subprocess.Popen(["uv","run","shiny","run","tests/playwright/render_pygwalker/app.py","--port",str(PORT)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
time.sleep(6)
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(); page = b.new_page(viewport={"width":1200,"height":900})
        page.goto(f"http://127.0.0.1:{PORT}"); page.wait_for_timeout(8000)
        js = """() => { const out={}; for (const id of ['explorer','explicit_height','widget_height']) {
           const el=document.querySelector('#'+id); const chain=[]; let e=el;
           for (let i=0;i<5 && e;i++){const cs=getComputedStyle(e); chain.push([e.tagName,e.className,e.getAttribute('style'),cs.height,cs.minHeight,cs.display,cs.overflow]); e=e.firstElementChild;}
           out[id]=chain;} return out}"""
        for k,v in page.evaluate(js).items():
            print(k)
            for c in v: print("  ",c)
        b.close()
finally:
    p.terminate()
