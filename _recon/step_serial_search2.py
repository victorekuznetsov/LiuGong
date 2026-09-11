from playwright.sync_api import sync_playwright
import json

reqs = []
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.goto("http://epc.liugong.com:800/usage/vin/LGC9125FARC135673", wait_until="load", timeout=20000)
    page.wait_for_timeout(1200)

    def on_request(req):
        if req.method == "POST" or "serial" in req.url.lower() or "feature" in req.url.lower():
            reqs.append({"method": req.method, "url": req.url, "post": req.post_data})
    page.on("request", on_request)

    page.click("li[data-action='part-serial-num-show']", timeout=5000)
    page.wait_for_timeout(1000)
    page.screenshot(path="_recon/serial_dialog2.png", full_page=True)
    with open("_recon/serial_reqs2.json","w",encoding="utf-8") as f:
        json.dump(reqs, f, ensure_ascii=False, indent=2)
    print("captured", len(reqs))
