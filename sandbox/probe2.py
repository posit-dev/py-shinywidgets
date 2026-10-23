import sys
from playwright.sync_api import sync_playwright
JS="""()=>['fill','explicit','layouth'].map(id=>{const o=document.getElementById(id);const c=o.querySelector('canvas');const b=o.getBoundingClientRect();const cb=c&&c.getBoundingClientRect();return [id,Math.round(b.width),Math.round(b.height),cb&&Math.round(cb.width),cb&&Math.round(cb.height)]})"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":900,"height":900})
    pg.goto(sys.argv[1]); pg.wait_for_timeout(6000)
    print(pg.evaluate(JS))
    pg.set_viewport_size({"width":600,"height":900}); pg.wait_for_timeout(1500)
    print(pg.evaluate(JS))
    pg.screenshot(path="sandbox/shot2.png", full_page=True)
