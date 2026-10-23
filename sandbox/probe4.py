from playwright.sync_api import sync_playwright
P=open('sandbox/port').read().strip()
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width":1100,"height":700})
    pg.goto(f"http://localhost:{P}")
    pg.wait_for_selector("#scene canvas", timeout=60000); pg.wait_for_timeout(2500)
    print(pg.evaluate("""() => { const out=[]; let e=document.querySelector('#scene canvas'); while(e && e!==document.body){const b=e.getBoundingClientRect(); const cs=getComputedStyle(e); out.push(e.tagName+'.'+String(e.className).slice(0,60)+' h='+Math.round(b.height)+' flex='+cs.flex+' disp='+cs.display+' minh='+cs.minHeight+' maxh='+cs.maxHeight); e=e.parentElement} return out.join('\\n')}"""))
    b.close()
