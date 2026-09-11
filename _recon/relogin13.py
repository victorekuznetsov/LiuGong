from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    with ctx.expect_page() as newpage_info:
        page.click("text=EPC")
    newpage = newpage_info.value
    newpage.wait_for_load_state("load", timeout=30000)
    newpage.wait_for_timeout(2000)
    print("NEW URL:", newpage.url)
    print("NEW TITLE:", newpage.title())
    newpage.screenshot(path="_recon/relogin13.png", full_page=True)
