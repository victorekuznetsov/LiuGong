from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    page.wait_for_timeout(1000)
    cap = page.query_selector("#validateCode")
    print("cap:", cap)
    if cap:
        cap.screenshot(path="_recon/captcha3.png")
    page.screenshot(path="_recon/relogin7_full.png", full_page=True)
