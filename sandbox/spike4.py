import subprocess, time, sys, json
from playwright.sync_api import sync_playwright
PORT=int(sys.argv[1])
p = subprocess.Popen(["uv","run","shiny","run","tests/playwright/render_pygwalker/app.py","--port",str(PORT)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
time.sleep(6)
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(); page = b.new_page(viewport={"width":1200,"height":900})
        page.goto(f"http://127.0.0.1:{PORT}"); page.wait_for_timeout(8000)
        print(page.evaluate("""() => { const out=[]; let e=document.querySelector('#explicit_height .p-2 > .overflow-y-auto');
          for (let i=0;i<12 && e;i++){ const cs=getComputedStyle(e); out.push([e.tagName,e.className.toString().slice(0,60),e.getAttribute('style'),cs.height,cs.minHeight,cs.display,cs.flexDirection].join(' | ')); e=e.firstElementChild;}
          return out.join('\\n')}"""))
        b.close()
finally:
    p.terminate()
