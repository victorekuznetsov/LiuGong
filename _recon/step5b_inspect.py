from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9333")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    html = page.content()
    with open("_recon/step5b_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    inputs = page.query_selector_all("input")
    for inp in inputs:
        print(inp.get_attribute("name"), inp.get_attribute("id"), inp.get_attribute("type"), inp.get_attribute("placeholder"))
