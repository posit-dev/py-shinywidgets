import sys
from playwright.sync_api import sync_playwright
JS="""()=>['fill','explicit'].map(id=>{const o=document.getElementById(id);const lm=o.children[0];const k=lm.children[0];const c=o.querySelector('canvas');const r=e=>{const b=e.getBoundingClientRect();return [Math.round(b.width),Math.round(b.height)]};return [id,r(o),r(lm),r(k),r(c),c.style.width,c.style.height,c.width,c.height]})"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":900,"height":900})
    pg.goto(sys.argv[1]); pg.wait_for_timeout(5000)
    pg.evaluate("""()=>{
      for (const id of ['fill','explicit']) { const o=document.getElementById(id); const lm=o.children[0]; const c=lm.children[0];
        c.style.width='100%';
        if (id==='explicit'){ lm.style.height='100%'; c.style.height='100%'; } }
    }""")
    pg.set_viewport_size({"width":600,"height":900}); pg.wait_for_timeout(1500)
    print(pg.evaluate(JS))
    pg.evaluate("window.dispatchEvent(new Event('resize'))"); pg.wait_for_timeout(1000)
    print(pg.evaluate(JS))
