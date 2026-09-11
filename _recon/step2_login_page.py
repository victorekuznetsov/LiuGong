from playwright.sync_api import sync_playwright

URL = "https://ssoweb.liugong.com/jsp/custompage/0/usergateway/userapplist.jsp"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
        locale="zh-CN",
        viewport={"width":1366,"height":900},
    )
    page = ctx.new_page()
    try:
        page.goto("https://ssoweb.liugong.com/", wait_until="load", timeout=20000)
    except Exception as e:
        print("root err", e)
    page.wait_for_timeout(2000)
    print("ROOT TITLE:", page.title())
    page.screenshot(path="_recon/step2_root.png", full_page=True)

    try:
        page.goto(URL, wait_until="load", timeout=20000)
    except Exception as e:
        print("target err", e)
    page.wait_for_timeout(2000)
    print("TARGET TITLE:", page.title())
    print("TARGET URL:", page.url)
    page.screenshot(path="_recon/step2_target.png", full_page=True)
    with open("_recon/step2_target.html", "w", encoding="utf-8") as f:
        f.write(page.content())
    browser.close()
print("done")
