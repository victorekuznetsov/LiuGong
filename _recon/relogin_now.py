from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222", timeout=90000)
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.goto("https://ssoweb.liugong.com/login/welcome", wait_until="load", timeout=30000)
    page.wait_for_timeout(1000)
    texts = page.query_selector_all("input[type='text']")
    pwds = page.query_selector_all("input[type='password']")
    if pwds:
        texts[0].fill("kuznetsovve@industrservice.ru")
        pwds[0].fill("lgdms@1234")
        page.wait_for_timeout(600)
        page.screenshot(path="_recon/relogin_now.png", full_page=True)
        print("login form filled, need captcha")
    else:
        print("already logged in?", page.url, page.title())
        page.screenshot(path="_recon/relogin_now.png", full_page=True)
