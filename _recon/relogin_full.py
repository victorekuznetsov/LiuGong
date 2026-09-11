from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://ssoweb.liugong.com/login/welcome", wait_until="load", timeout=20000)
    page.wait_for_timeout(1000)
    page.click("button:has-text('OK')", timeout=2000) if page.query_selector("button:has-text('OK')") else None
    page.fill("input[type='text']", "kuznetsovve@industrservice.ru")
    page.fill("input[type='password']", "lgdms@1234")
    page.wait_for_timeout(800)
    page.screenshot(path="_recon/relogin_full.png", full_page=True)
    print("ready for captcha read")
