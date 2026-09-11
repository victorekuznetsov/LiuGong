from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    page.goto("https://ssoweb.liugong.com/jsp/custompage/0/usergateway/userapplist.jsp", wait_until="load", timeout=30000)
    page.wait_for_timeout(1500)
    page.screenshot(path="_recon/relogin11.png", full_page=True)
    # find link/onclick around EPC icon
    html = page.content()
    with open("_recon/relogin11.html","w",encoding="utf-8") as f:
        f.write(html)
