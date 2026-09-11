from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://ssoweb.liugong.com/jsp/custompage/0/usergateway/userapplist.jsp", wait_until="load", timeout=20000)
    page.wait_for_timeout(2000)
    page.screenshot(path="_recon/sis_portal.png", full_page=True)

    with ctx.expect_page(timeout=15000) as newpage_info:
        page.click("text=SIS")
    newpage = newpage_info.value
    newpage.wait_for_load_state("load", timeout=30000)
    newpage.wait_for_timeout(2000)
    print("SIS URL:", newpage.url)
    print("SIS TITLE:", newpage.title())
    newpage.screenshot(path="_recon/sis_landing.png", full_page=True)
