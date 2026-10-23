from playwright.sync_api import sync_playwright
M = """() => { const out=[]; let e=document.querySelector('#explorer'); while(e && e!==document.body){const cs=getComputedStyle(e); out.push([e.tagName,String(e.className).slice(0,70),Math.round(e.getBoundingClientRect().height),cs.display,cs.flex,cs.overflow, cs.maxHeight].join(' | ')); e=e.parentElement;} return out.join('\\n')}"""
with sync_playwright() as pw:
    b = pw.chromium.launch(); page = b.new_page(viewport={"width":1200,"height":800})
    page.goto("http://127.0.0.1:30456/"); page.get_by_text("Field List").wait_for(timeout=30000); page.wait_for_timeout(1500)
    print(page.evaluate(M))
    b.close()
