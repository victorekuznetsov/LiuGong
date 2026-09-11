from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    page.wait_for_timeout(1000)
    page.screenshot(path="_recon/sis_home.png", full_page=True)
    print(page.url, page.title())
