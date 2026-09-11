from playwright.sync_api import sync_playwright
import json

reqs = []
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    page.bring_to_front()

    def on_request(req):
        if "usage/parts" in req.url or "childNode" in req.url or "legend-file" in req.url:
            reqs.append({"method": req.method, "url": req.url, "post": req.post_data})
    page.on("request", on_request)

    page.click("text=动力系统")
    page.wait_for_timeout(800)
    page.screenshot(path="_recon/ui_click1.png", full_page=True)

    # find first expanded child and click it
    page.click("text=燃油系统")
    page.wait_for_timeout(1500)
    page.screenshot(path="_recon/ui_click2.png", full_page=True)

    with open("_recon/ui_click_reqs.json","w",encoding="utf-8") as f:
        json.dump(reqs, f, ensure_ascii=False, indent=2)
    print("captured", len(reqs))
