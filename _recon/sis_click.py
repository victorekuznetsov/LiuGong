from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    try:
        with ctx.expect_page(timeout=15000) as newpage_info:
            page.click("text=SIS")
        newpage = newpage_info.value
        newpage.wait_for_load_state("domcontentloaded", timeout=20000)
        newpage.wait_for_timeout(2000)
        print("SIS URL:", newpage.url)
        print("SIS TITLE:", newpage.title())
        newpage.screenshot(path="_recon/sis_landing2.png", full_page=True)
    except Exception as e:
        print("no new page, same-tab nav?", e)
        page.wait_for_timeout(2000)
        print("current URL:", page.url, page.title())
        page.screenshot(path="_recon/sis_landing2.png", full_page=True)
