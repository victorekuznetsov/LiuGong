from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    page.click("text=登录")
    page.wait_for_timeout(3000)
    print("URL:", page.url)
    print("TITLE:", page.title())
    page.screenshot(path="_recon/relogin5.png", full_page=True)
