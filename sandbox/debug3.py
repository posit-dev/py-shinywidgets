import time, json, base64
from pathlib import PurePath
from playwright.sync_api import sync_playwright
from shiny.run._run import shiny_app_gen

sa_gen = shiny_app_gen(PurePath("tests/playwright/render_ipycanvas/app.py"), env={})
app = next(sa_gen)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        seen = {"open": 0, "msg": 0}
        def on_ws(ws):
            def on_frame(payload):
                try:
                    s = payload if isinstance(payload, str) else payload.decode("utf-8", "replace")
                except Exception:
                    return
                if "shinywidgets_comm_open" in s and seen["open"] < 6:
                    seen["open"] += 1
                    i = s.find("shinywidgets_comm_open")
                    print("OPEN", s[i:i+260].replace("\\n", " ")[:260])
                elif "shinywidgets_comm_msg" in s and seen["msg"] < 3:
                    seen["msg"] += 1
                    i = s.find("shinywidgets_comm_msg")
                    print("MSG", s[i:i+800][:800])
            ws.on("framereceived", on_frame)
        page.on("websocket", on_ws)
        page.on("pageerror", lambda err: None)
        page.goto(app.url)
        time.sleep(5)
        browser.close()
finally:
    pass
