import subprocess, time, sys
from playwright.sync_api import sync_playwright
p = subprocess.Popen(["uv","run","shiny","run","sandbox/spike.py","--port","37696"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
time.sleep(6)
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(); page = b.new_page(viewport={"width":1100,"height":800})
        page.on("console", lambda m: print("CONSOLE", m.type, m.text[:200]))
        page.on("pageerror", lambda e: print("PAGEERR", e))
        page.on("response", lambda r: print("RESP", r.status, r.url[:120]) if r.status>=400 or "localhost" not in r.url and "127.0.0.1" not in r.url else None)
        page.on("requestfailed", lambda r: print("REQFAIL", r.url[:120]))
        page.goto("http://127.0.0.1:37696"); page.wait_for_timeout(8000)
        page.screenshot(path="sandbox/spike.png")
        print(page.evaluate("""() => { const r=s=>{const e=document.querySelector(s); if(!e) return null; const b=e.getBoundingClientRect(); return [b.x,b.y,b.width,b.height]}; 
          return {card: r('.card'), out: r('#w'), lm: r('#w > .lm-Widget'), kids: [...document.querySelector('#w > .lm-Widget').children].map(c=>[c.tagName,c.className, JSON.stringify(c.getBoundingClientRect())])}}"""))
        b.close()
finally:
    p.terminate(); print(p.stdout.read()[-3000:])
