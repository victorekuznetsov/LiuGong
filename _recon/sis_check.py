from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    pages = ctx.pages
    for i, pg in enumerate(pages):
        print(i, pg.url, "|", pg.title())
    page = pages[-1]
    page.wait_for_timeout(2000)
    print("final:", page.url, page.title())
    page.screenshot(path="_recon/sis_landing3.png", full_page=True)
    with open("_recon/sis_landing3.html", "w", encoding="utf-8") as f:
        f.write(page.content())
