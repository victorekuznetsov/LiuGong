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

    # find the select element (even if hidden) and click a broader container
    el = page.query_selector("select")
    print("select outerHTML snippet:", page.eval_on_selector("select", "el => el.outerHTML.slice(0,500)") if el else None)

    # try clicking the visible dropdown box at that location
    box = page.query_selector("div.chosen-container, .select2-container, .dropdown, .combobox")
    print("box found:", box is not None)

    page.mouse.click(620, 196)
    page.wait_for_timeout(1500)
    page.screenshot(path="_recon/step8_after_click.png", full_page=True)

    with open("_recon/step8_requests.json","w",encoding="utf-8") as f:
        json.dump(reqs, f, ensure_ascii=False, indent=2)
    print("captured:", len(reqs))
