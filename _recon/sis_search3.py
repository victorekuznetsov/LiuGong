from playwright.sync_api import sync_playwright
import json

reqs = []
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]

    def on_request(req):
        if req.method in ("GET","POST"):
            reqs.append({"method": req.method, "url": req.url, "post": req.post_data})
    page.on("request", on_request)

    box = page.query_selector("input[placeholder*='整机物料号']")
    box.fill("")
    box.fill("LGC9125FARC135673")
    page.wait_for_timeout(300)
    # click the magnifier icon right after the input (svg/i with search icon), use the visible search button near box
    page.click("input[placeholder*='整机物料号'] ~ * >> svg, input[placeholder*='整机物料号'] + span", timeout=3000)
    page.wait_for_timeout(2500)
    print("URL:", page.url)
    page.screenshot(path="_recon/sis_search3.png", full_page=True)
    with open("_recon/sis_search3_reqs.json","w",encoding="utf-8") as f:
        json.dump(reqs, f, ensure_ascii=False, indent=2)
    print("reqs:", len(reqs))
