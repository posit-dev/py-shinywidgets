import sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width":900,"height":1000})
    pg.goto("http://127.0.0.1:19378")
    pg.wait_for_selector("#widget_height .embedding-atlas-widget-container"); pg.wait_for_timeout(2000)
    for sel in ("#output_height","#widget_height"):
        print(sel, pg.evaluate("""(sel)=>{let e=document.querySelector(sel);const out=[];while(e&&out.length<5){const cs=getComputedStyle(e);out.push([e.tagName,String(e.className).slice(0,50),e.getAttribute('style'),e.getBoundingClientRect().height,cs.display,cs.overflow]);e=e.firstElementChild}return out}""", sel))
    b.close()
