from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    for pg in ctx.pages:
        if "sis.liugong.com" in pg.url:
            pg.wait_for_timeout(1000)
            pg.screenshot(path="_recon/sis_struct_now.png", full_page=True)
            print(pg.url)
            with open("_recon/sis_struct_now.html","w",encoding="utf-8") as f:
                f.write(pg.content())
