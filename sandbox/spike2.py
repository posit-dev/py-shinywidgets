import subprocess, time, sys, json
from playwright.sync_api import sync_playwright
PORT=int(sys.argv[1])
p = subprocess.Popen(["uv","run","shiny","run","tests/playwright/render_pygwalker/app.py","--port",str(PORT)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
time.sleep(6)
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(); page = b.new_page(viewport={"width":1200,"height":900})
        page.on("pageerror", lambda e: print("PAGEERR", e))
        page.on("console", lambda m: print("CONSOLE", m.type, m.text[:200]) if m.type=="error" else None)
        page.goto(f"http://127.0.0.1:{PORT}"); page.wait_for_timeout(8000)
        page.screenshot(path="sandbox/spike2.png", full_page=True)
        js = """() => { const r=s=>{const e=document.querySelector(s); if(!e) return null; const b=e.getBoundingClientRect(); return [b.x,b.y,b.width,b.height].map(Math.round)};
          return {card: r('#fill_card'), cardbody: r('#fill_card .card-body'), out: r('#explorer'), lm: r('#explorer > .lm-Widget'), inner: r('#explorer > .lm-Widget > div'),
           e_out: r('#explicit_height'), e_lm: r('#explicit_height > .lm-Widget'), e_in: r('#explicit_height > .lm-Widget > div'),
           w_out: r('#widget_height'), w_lm: r('#widget_height > .lm-Widget'), w_in: r('#widget_height > .lm-Widget > div')}}"""
        print(json.dumps(page.evaluate(js)))
        b.close()
finally:
    p.terminate()
