from playwright.sync_api import sync_playwright
import json

reqs = []

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9333")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    page.bring_to_front()

    def on_request(req):
        reqs.append({"method": req.method, "url": req.url, "post": req.post_data, "type": req.resource_type})
    page.on("request", on_request)

    page.goto("http://epc.liugong.com:800/usage/vin/LGC9125FARC135673", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    page.screenshot(path="_recon/step9_after_reload.png", full_page=True)
    with open("_recon/step9_requests.json","w",encoding="utf-8") as f:
        json.dump(reqs, f, ensure_ascii=False, indent=2)
    print("captured:", len(reqs))
