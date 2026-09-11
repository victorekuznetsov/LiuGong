from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    resp = page.evaluate("""async () => {
        const r = await fetch('/legend-usage-group/tree/vin/', {
            method: 'POST',
            headers: {'Content-Type':'application/x-www-form-urlencoded'},
            body: 'vin=LGC9125FARC135673',
            credentials: 'include'
        });
        return await r.text();
    }""")
    with open("_recon/tree_vin.json", "w", encoding="utf-8") as f:
        f.write(resp)
    print(resp[:2000])
