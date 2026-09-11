from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9333")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    resp = page.evaluate("""async () => {
        const r = await fetch('/product/tree', {credentials:'include'});
        return await r.text();
    }""")
    print(resp[:3000])
