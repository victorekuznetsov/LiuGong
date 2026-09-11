from playwright.sync_api import sync_playwright
import json

reqs = []

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9333")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    page.bring_to_front()

    def on_request(req):
        if "epc.liugong.com" in req.url and any(x in req.url for x in ["api","ajax","service",".do",".json","query","search"]):
            reqs.append({"method": req.method, "url": req.url, "post": req.post_data})

    page.on("request", on_request)

    # Make sure "整机序列号" tab is selected, then type serial
    page.click("text=整机序列号")
    page.wait_for_timeout(300)
    search_box = page.query_selector("input[type='text']")
    search_box.fill("LGC9125FARC135673")
    page.wait_for_timeout(300)
    page.keyboard.press("Enter")
    page.wait_for_timeout(4000)
    print("URL after search:", page.url)
    page.screenshot(path="_recon/step6_search_result.png", full_page=True)
    with open("_recon/step6_search_result.html","w",encoding="utf-8") as f:
        f.write(page.content())

    with open("_recon/step6_requests.json","w",encoding="utf-8") as f:
        json.dump(reqs, f, ensure_ascii=False, indent=2)
    print("captured requests:", len(reqs))
