import sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":900,"height":800})
    errs=[]
    pg.on("console", lambda m: errs.append((m.type,m.text)) if m.type in("error","warning") else None)
    pg.on("pageerror", lambda e: errs.append(("pageerror",str(e))))
    pg.on("response", lambda r: errs.append(("http",r.status,r.url)) if r.status>=400 else None)
    pg.goto(sys.argv[1]); pg.wait_for_timeout(6000)
    print(errs)
    print(pg.evaluate("""()=>{const r=e=>{const b=e.getBoundingClientRect();return [e.tagName,e.className,Math.round(b.x),Math.round(b.y),Math.round(b.width),Math.round(b.height),e.style.cssText]};
      const out=[];let e=document.querySelector('canvas');while(e&&e.id!=='v'){out.push(r(e));e=e.parentElement}; if(e) out.push(r(e)); return out}"""))
    pg.screenshot(path="sandbox/shot.png")
