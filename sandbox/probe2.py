from playwright.sync_api import sync_playwright
P=open('sandbox/port').read().strip()
MEASURE="""() => { const r=s=>{const e=document.querySelector(s); if(!e) return null; const b=e.getBoundingClientRect(); return [Math.round(b.width),Math.round(b.height)]};
 return {fill_out:r('#fill_plot'), fill_canvas:r('#fill_plot canvas'), fill_card:r('#fill_card'), fixed_out:r('#fixed_plot'), fixed_canvas:r('#fixed_plot canvas'), sized_out:r('#sized_output'), sized_canvas:r('#sized_output canvas'), ncanv:[...document.querySelectorAll('#fill_plot canvas')].map(c=>[c.className,c.width,c.height])}}"""
with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width":900,"height":900})
    pg.on("pageerror", lambda e: print("PAGEERR", e))
    pg.on("console", lambda m: print("ERR", m.text[:200]) if m.type=="error" else None)
    pg.goto(f"http://localhost:{P}")
    pg.wait_for_selector("#fill_plot canvas", timeout=60000)
    pg.wait_for_selector("#sized_output canvas", timeout=60000)
    pg.wait_for_timeout(3000)
    print(pg.evaluate(MEASURE))
    pg.set_viewport_size({"width":600,"height":900}); pg.wait_for_timeout(1500)
    print(pg.evaluate(MEASURE))
    print(pg.locator("#camera").inner_text())
    c=pg.locator("#fill_plot canvas").first; bb=c.bounding_box()
    pg.mouse.move(bb['x']+100,bb['y']+100); pg.mouse.down(); pg.mouse.move(bb['x']+200,bb['y']+160,steps=10); pg.mouse.up()
    pg.wait_for_timeout(2000)
    print(pg.locator("#camera").inner_text())
    pg.screenshot(path="sandbox/shot.png", full_page=True)
    b.close()
