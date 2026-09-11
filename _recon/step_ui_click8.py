from playwright.sync_api import sync_playwright
import json

reqs = []
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    page.bring_to_front()

    def on_request(req):
        if any(k in req.url for k in ["usage/parts","childNode","legend-file"]):
            reqs.append({"method": req.method, "url": req.url, "post": req.post_data})
    page.on("request", on_request)

    # expand level-2 node 60C6073 via its caret
    page.click("li[data-id='60C6073'] > a > span[data-area='group-icon']")
    page.wait_for_timeout(1000)
    page.screenshot(path="_recon/ui_click9.png", full_page=True)

    # click level-3 child node
    page.click("li[data-id='60C6073_00'] > a > b")
    page.wait_for_timeout(4000)
    page.screenshot(path="_recon/ui_click10.png", full_page=True)

    with open("_recon/ui_click_reqs8.json","w",encoding="utf-8") as f:
        json.dump(reqs, f, ensure_ascii=False, indent=2)
    print(json.dumps(reqs, ensure_ascii=False, indent=2)[:3000])
