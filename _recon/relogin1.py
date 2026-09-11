from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.goto("https://ssoweb.liugong.com/login/welcome", wait_until="load", timeout=30000)
    page.wait_for_timeout(1000)
    page.fill("input[type='text']", "kuznetsovve@industrservice.ru")
    page.fill("input[type='password']", "lgdms@1234")
    page.wait_for_timeout(300)
    im = page.query_selector("img")
    page.screenshot(path="_recon/relogin1.png", full_page=True)
    print("done, url:", page.url)
