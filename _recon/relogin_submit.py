from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    page.fill("input[maxlength='4'], input[placeholder='验证码']", "5899")
    inputs = page.query_selector_all("input[type='text']")
    for inp in inputs:
        if inp.get_attribute("value") in (None, ""):
            inp.fill("5899")
    page.click("text=登录")
    page.wait_for_timeout(2500)
    print("URL:", page.url, "TITLE:", page.title())

    page.goto("https://ssoweb.liugong.com/jsp/custompage/0/usergateway/userapplist.jsp", wait_until="load", timeout=20000)
    page.wait_for_timeout(2500)
    print("URL2:", page.url, "TITLE2:", page.title())
    page.screenshot(path="_recon/portal_after_login.png", full_page=True)

    links = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('a,p,div,img').forEach(el => {
            const t = (el.textContent||'').trim();
            if (t === 'SIS' || t === 'EPC' || t === 'EPC2') {
                out.push({tag: el.tagName, text: t,
                          html: el.outerHTML.slice(0,200),
                          parentHtml: el.parentElement ? el.parentElement.outerHTML.slice(0,300) : null});
            }
        });
        return out;
    }""")
    print(json.dumps(links, ensure_ascii=False, indent=2))
