from playwright.sync_api import sync_playwright
JS="""(id)=>{const o=document.getElementById(id);const c=o.querySelector('canvas').getBoundingClientRect();const b=o.getBoundingClientRect();return {out:[b.width,b.height],canvas:[c.width,c.height]}}"""
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":900,"height":900}); pg.goto("http://127.0.0.1:18315"); pg.wait_for_timeout(5000)
    fc=pg.locator("#fill_container").bounding_box()
    print("container",fc, pg.evaluate(JS,"view"), pg.evaluate(JS,"fixed"))
    pg.set_viewport_size({"width":600,"height":900}); pg.wait_for_timeout(1500)
    print("narrow",pg.locator("#fill_container").bounding_box(), pg.evaluate(JS,"view"))
