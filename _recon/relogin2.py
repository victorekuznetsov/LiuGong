from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[-1]
    page.wait_for_timeout(1500)
    page.screenshot(path="_recon/relogin2.png", full_page=True)
    cap = page.query_selector("#authCode, #verifyCode, .yzm, img[id*='code'], img[id*='Code']")
    print("cap found:", cap)
    imgs = page.query_selector_all("img")
    for im in imgs:
        print(im.get_attribute("id"), im.get_attribute("src"))
