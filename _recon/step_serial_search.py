from playwright.sync_api import sync_playwright
import json

reqs = []
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    page.bring_to_front()
    page.goto("http://epc.liugong.com:800/usage/vin/LGC9125FARC135673", wait_until="load", timeout=30000)
    page.wait_for_timeout(1500)

    def on_request(req):
        if req.method == "POST" or "serial" in req.url.lower() or "feature" in req.url.lower():
            reqs.append({"method": req.method, "url": req.url, "post": req.post_data})
    page.on("request", on_request)

    page.click("li[data-action='part-serial-num-show']")
    page.wait_for_timeout(1500)
    page.screenshot(path="_recon/serial_dialog.png", full_page=True)
    with open("_recon/serial_reqs.json","w",encoding="utf-8") as f:
        json.dump(reqs, f, ensure_ascii=False, indent=2)
    print(len(reqs))
