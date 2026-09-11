from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://ssoweb.liugong.com/login/welcome", wait_until="load", timeout=30000)
    page.wait_for_timeout(1000)
    page.fill("input[type='text']", "kuznetsovve@industrservice.ru")
    page.fill("input[type='password']", "lgdms@1234")
    page.wait_for_timeout(500)
    page.screenshot(path="_recon/relogin6.png", full_page=True)
    print("ready")
