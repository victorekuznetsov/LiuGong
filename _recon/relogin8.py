from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    imgs = page.query_selector_all("img")
    print("count:", len(imgs))
    for im in imgs:
        print(im.get_attribute("id"), "|", im.get_attribute("src"), "|", im.bounding_box())
