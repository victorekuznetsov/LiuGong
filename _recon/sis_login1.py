from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    page.wait_for_timeout(500)
    texts = page.query_selector_all("input[type='text']")
    pwds = page.query_selector_all("input[type='password']")
    print("texts:", len(texts), "pwds:", len(pwds))
    texts[0].fill("kuznetsovve@industrservice.ru")
    pwds[0].fill("lgdms@1234")
    page.wait_for_timeout(600)
    page.screenshot(path="_recon/sis_login1.png", full_page=True)
