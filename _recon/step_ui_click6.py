from playwright.sync_api import sync_playwright
import json

reqs = []
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    page.bring_to_front()

    def on_request(req):
        if any(k in req.url for k in ["usage/parts","childNode","legend-file","legend-usage-group","legend"]):
            reqs.append({"method": req.method, "url": req.url, "post": req.post_data})
    page.on("request", on_request)

    page.click("#group-content >> text=60C6073_燃油系统")
    page.wait_for_timeout(3000)
    page.screenshot(path="_recon/ui_click7.png", full_page=True)

    with open("_recon/ui_click_reqs6.json","w",encoding="utf-8") as f:
        json.dump(reqs, f, ensure_ascii=False, indent=2)
    print(json.dumps(reqs, ensure_ascii=False, indent=2)[:2000])
