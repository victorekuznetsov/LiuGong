from playwright.sync_api import sync_playwright
import re

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    html = page.content()
    for m in re.finditer(r'lang[=/"\']{1,3}([a-zA-Z_\-]{2,8})', html):
        print(m.group(0))
