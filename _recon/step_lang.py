from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    # inspect the language switch menu
    html = page.content()
    import re
    idx = html.find('语言切换')
    print(html[idx-200:idx+2500])
