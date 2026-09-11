from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    page.bring_to_front()
    page.wait_for_timeout(500)
    page.screenshot(path="_recon/relogin4.png", full_page=True)
    imgs = page.query_selector_all("img")
    for im in imgs:
        print(im.get_attribute("id"), im.get_attribute("src"))
