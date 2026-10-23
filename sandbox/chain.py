import sys
from playwright.sync_api import sync_playwright
url, sel, shot = sys.argv[1:4]
JS="""(sel)=>{const r=e=>{const b=e.getBoundingClientRect();return [e.tagName+'.'+String(e.className).slice(0,50),Math.round(b.y),Math.round(b.width),Math.round(b.height)]};let e=document.querySelector(sel);const o=[];while(e&&e.tagName!=='BODY'){o.push(r(e));e=e.parentElement}return o}"""
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1100,"height":700})
    pg.goto(url); pg.wait_for_selector(sel, timeout=30000); pg.wait_for_timeout(6000)
    for r in pg.evaluate(JS, sel): print(r)
    pg.screenshot(path=shot)
