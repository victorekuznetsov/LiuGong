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
    def on_response(res):
        pass
    page.on("request", on_request)

    # click the dropdown (select element) shown near top - try select options
    sel = page.query_selector("select")
    if sel:
        options = page.eval_on_selector("select", "el => Array.from(el.options).map(o => [o.value, o.text])")
        print("OPTIONS:", options[:20], "... total", len(options))
    else:
        print("no select found, trying other approach")

    page.wait_for_timeout(500)
    with open("_recon/step7_requests.json","w",encoding="utf-8") as f:
        json.dump(reqs, f, ensure_ascii=False, indent=2)
