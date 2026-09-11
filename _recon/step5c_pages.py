from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9333")
    for ci, ctx in enumerate(browser.contexts):
        for pi, page in enumerate(ctx.pages):
            print(ci, pi, page.url, "|", page.title())
