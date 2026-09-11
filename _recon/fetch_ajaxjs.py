from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    txt = page.evaluate("""async () => {
        const r = await fetch('/js/libs/private/ajax.js', {credentials:'include'});
        return await r.text();
    }""")
    with open("_recon/js_ajax.js", "w", encoding="utf-8") as f:
        f.write(txt)
    print(len(txt))
