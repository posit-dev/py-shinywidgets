from playwright.sync_api import sync_playwright
import sys, json
with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width":900,"height":800})
    pg.on("console", lambda m: None)
    pg.on("pageerror", lambda e: print("PAGEERR", e))
    pg.on("response", lambda r: print("HTTP", r.status, r.url) if r.status>=400 else None)
    pg.goto("http://localhost:55043")
    pg.wait_for_selector("#p canvas", timeout=60000)
    pg.wait_for_timeout(3000)
    print(pg.evaluate("""() => { const o=document.querySelector('#p'); const r=e=>{const b=e.getBoundingClientRect();return [Math.round(b.width),Math.round(b.height)]};
    const out=[]; const walk=(e,d)=>{ if(d>3) return; out.push('  '.repeat(d)+e.tagName+'.'+(e.className||'').toString().slice(0,50)+' '+r(e)+' '+(e.getAttribute('style')||'').slice(0,80)); for(const c of e.children) walk(c,d+1)}; walk(o,0); return out.join('\\n')}"""))
    pg.screenshot(path="sandbox/shot.png")
    b.close()
