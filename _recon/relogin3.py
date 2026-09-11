from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    for i, pg in enumerate(ctx.pages):
        print(i, pg.url, pg.title())
