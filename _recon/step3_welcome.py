from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
        locale="zh-CN",
        viewport={"width":1366,"height":900},
        storage_state=None,
    )
    page = ctx.new_page()
    page.goto("https://ssoweb.liugong.com/login/welcome", wait_until="load", timeout=30000)
    page.wait_for_timeout(1500)
    print("TITLE:", page.title())
    print("URL:", page.url)
    page.screenshot(path="_recon/step3_welcome.png", full_page=True)
    with open("_recon/step3_welcome.html", "w", encoding="utf-8") as f:
        f.write(page.content())
    ctx.storage_state(path="session/storage_state.json")
    browser.close()
print("done")
