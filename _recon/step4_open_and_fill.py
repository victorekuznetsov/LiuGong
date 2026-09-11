from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(
        channel="chrome", headless=False,
        args=["--disable-blink-features=AutomationControlled", "--remote-debugging-port=9333"]
    )
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
        locale="zh-CN",
        viewport={"width":1366,"height":900},
    )
    page = ctx.new_page()
    page.goto("https://ssoweb.liugong.com/login/welcome", wait_until="load", timeout=30000)
    page.wait_for_timeout(1000)
    page.fill("input[name='j_username'], #username, input[type='text']", "kuznetsovve@industrservice.ru")
    page.wait_for_timeout(300)
    # find password field
    page.fill("input[type='password']", "lgdms@1234")
    page.wait_for_timeout(300)
    cap = page.query_selector("img[src*='captcha'], img[src*='verify'], img[src*='code']")
    if cap:
        cap.screenshot(path="_recon/captcha.png")
        print("captcha src:", cap.get_attribute("src"))
    else:
        print("no captcha img found by selector, screenshotting full page")
        page.screenshot(path="_recon/step4_full.png", full_page=True)
    print("kept browser alive, sleeping 300s for CDP takeover on port 9333")
    time.sleep(300)
    browser.close()
