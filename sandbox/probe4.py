import sys
from playwright.sync_api import sync_playwright
JS="""()=>['fill','explicit','layouth'].map(id=>{const o=document.getElementById(id);const c=o.querySelector('canvas');const b=o.getBoundingClientRect();const cb=c&&c.getBoundingClientRect();return [id,Math.round(b.width),Math.round(b.height),cb&&Math.round(cb.width),cb&&Math.round(cb.height)]})"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":900,"height":900})
    pg.goto(sys.argv[1]); pg.wait_for_timeout(5000)
    pg.evaluate("""()=>{
      for (const id of ['fill','explicit']) { const o=document.getElementById(id); const lm=o.children[0]; const c=lm.children[0];
        c.style.width='100%';
        if (id==='explicit'){ lm.style.height='100%'; c.style.height='100%'; } }
    }""")
    pg.wait_for_timeout(1000)
    print(pg.evaluate(JS))
    pg.set_viewport_size({"width":600,"height":900}); pg.wait_for_timeout(1500)
    print(pg.evaluate(JS))
