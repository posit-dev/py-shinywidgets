import sys
from playwright.sync_api import sync_playwright
JS="""(id)=>{const o=document.getElementById(id);let e=o.querySelector('canvas');const out=[];while(e){const cs=getComputedStyle(e);const b=e.getBoundingClientRect();out.push([e.tagName,String(e.className).slice(0,40),Math.round(b.width),Math.round(b.height),cs.display,cs.flex,e.getAttribute('style')]);if(e===o)break;e=e.parentElement}return out}"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":900,"height":900})
    pg.goto(sys.argv[1]); pg.wait_for_timeout(6000)
    for i in ['fill','explicit','layouth']:
        print(i)
        for r in pg.evaluate(JS,i): print("  ",r)
