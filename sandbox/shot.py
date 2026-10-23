import sys, json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(args=sys.argv[2].split(",") if len(sys.argv)>2 else [])
    pg = b.new_page(viewport={"width":1000,"height":700})
    msgs=[]
    pg.on("console", lambda m: msgs.append(m.type+": "+m.text))
    pg.on("pageerror", lambda e: msgs.append("PAGEERR "+str(e)))
    pg.on("requestfailed", lambda r: msgs.append("REQFAIL "+r.url))
    pg.goto(sys.argv[1])
    pg.wait_for_timeout(8000)
    pg.screenshot(path="sandbox/shot.png")
    print(pg.evaluate("""()=>{
      const o=document.querySelector('#atlas'); const r=e=>{const b=e.getBoundingClientRect();return [b.x,b.y,b.width,b.height]};
      const out={out:r(o)}; let e=o.firstElementChild; let d=0; const chain=[];
      while(e&&d<8){chain.push([e.tagName,e.className.toString().slice(0,60),r(e), getComputedStyle(e).height]); e=e.firstElementChild; d++}
      out.chain=chain; out.card=r(document.querySelector('.card')); out.canvas=[...o.querySelectorAll('canvas')].map(r);return out}"""))
    print("\n".join(msgs))
    b.close()
