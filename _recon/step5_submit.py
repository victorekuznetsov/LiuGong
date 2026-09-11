from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9333")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    page.fill("input[name='verifyCode'], #verifyCode, input[maxlength='4']", "9567")
    page.wait_for_timeout(300)
    page.screenshot(path="_recon/step5_before_submit.png", full_page=True)
    page.click("text=登录")
    page.wait_for_timeout(3000)
    print("URL after submit:", page.url)
    print("TITLE:", page.title())
    page.screenshot(path="_recon/step5_after_submit.png", full_page=True)
    with open("_recon/step5_after_submit.html", "w", encoding="utf-8") as f:
        f.write(page.content())
    ctx.storage_state(path="session/storage_state.json")
    print("done, browser left open")
