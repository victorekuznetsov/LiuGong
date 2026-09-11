from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    for pg in list(ctx.pages):
        try:
            print("page:", pg.url)
        except Exception as e:
            print("dead page, closing:", e)
            try:
                pg.close()
            except Exception:
                pass
