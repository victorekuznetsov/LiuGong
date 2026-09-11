from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    resp = page.evaluate("""async () => {
        const params = new URLSearchParams({
            vin: 'LGC9125FARC135673',
            modelCode: '',
            systemCode: 'Y05',
            legendCode: '60C6073_003_00',
            parentPartNo: '60C6073'
        });
        const r = await fetch('/usage/parts?' + params.toString(), {credentials:'include'});
        return await r.text();
    }""")
    with open("_recon/parts_sample.json", "w", encoding="utf-8") as f:
        f.write(resp)
    print(resp[:3000])
