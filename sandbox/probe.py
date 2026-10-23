import subprocess, sys, time, json
from playwright.sync_api import sync_playwright
proc = subprocess.Popen([sys.executable, "-m", "shiny", "run", "sandbox/app.py", "--port", "48931"])
time.sleep(5)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width":1000,"height":800})
        errs=[]
        pg.on("console", lambda m: errs.append(m.text) if m.type=="error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("response", lambda r: errs.append("HTTP %s %s"%(r.status,r.url)) if r.status>=400 else None)
        pg.goto("http://localhost:48931"); time.sleep(6)
        print(pg.evaluate("""()=>{
          const out=document.querySelector('#m'); const r=e=>{const b=e.getBoundingClientRect();return [e.tagName, e.className.toString().slice(0,60), Math.round(b.width), Math.round(b.height)]};
          const res=[]; let e=out; const walk=(e,d)=>{ if(d>4) return; res.push('  '.repeat(d)+JSON.stringify(r(e))); for(const c of e.children) walk(c,d+1)}; walk(out,0); return res.join('\\n')}"""))
        print(errs)
        pg.screenshot(path="sandbox/shot.png")
finally:
    proc.terminate()
