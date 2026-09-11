from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9333")
    ctx = browser.contexts[0]
    p0, p1 = ctx.pages[0], ctx.pages[1]
    p0.screenshot(path="_recon/tab0_epc.png", full_page=True)
    p1.screenshot(path="_recon/tab1_sso.png", full_page=True)
    with open("_recon/tab0_epc.html","w",encoding="utf-8") as f: f.write(p0.content())
    with open("_recon/tab1_sso.html","w",encoding="utf-8") as f: f.write(p1.content())
    ctx.storage_state(path="session/storage_state.json")
    print("ok")
