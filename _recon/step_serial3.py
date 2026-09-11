from playwright.sync_api import sync_playwright
import json

reqs = []
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("http://epc.liugong.com:800/", wait_until="load", timeout=20000)
    page.wait_for_timeout(1000)
    print("logged in as:", page.title())

    page.goto("http://epc.liugong.com:800/usage/vin/LGC9125FARC135673", wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(1500)

    def on_request(req):
        if req.method == "POST":
            reqs.append({"method": req.method, "url": req.url, "post": req.post_data})
    page.on("request", on_request)

    page.click("li[data-action='part-serial-num-show']", timeout=5000)
    page.wait_for_timeout(1200)
    page.screenshot(path="_recon/serial_dialog3.png")

    with open("_recon/serial_reqs3.json","w",encoding="utf-8") as f:
        json.dump(reqs, f, ensure_ascii=False, indent=2)
    print("captured", len(reqs))
