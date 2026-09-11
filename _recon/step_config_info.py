from playwright.sync_api import sync_playwright
import json

reqs = []
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    page.click("#s_simnew31", timeout=1000) if False else None
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)

    def on_request(req):
        if req.method == "POST":
            reqs.append({"method": req.method, "url": req.url, "post": req.post_data})
    page.on("request", on_request)

    page.click("li[data-action='config-info-show']", timeout=5000)
    page.wait_for_timeout(1500)
    page.screenshot(path="_recon/config_dialog.png")
    with open("_recon/config_reqs.json","w",encoding="utf-8") as f:
        json.dump(reqs, f, ensure_ascii=False, indent=2)
    print(len(reqs))
