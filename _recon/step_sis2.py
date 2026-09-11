from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.goto("https://ssoweb.liugong.com/jsp/custompage/0/usergateway/userapplist.jsp", wait_until="load", timeout=20000)
    page.wait_for_timeout(2500)
    print("URL:", page.url, "TITLE:", page.title())
    page.screenshot(path="_recon/sis_portal2.png", full_page=True)
    links = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('a,p,div').forEach(el => {
            const t = (el.textContent||'').trim();
            if (t === 'SIS' || t === 'EPC' || t === 'EPC2') {
                out.push({tag: el.tagName, text: t, href: el.getAttribute('href'),
                          onclick: el.getAttribute('onclick'), parentHref: el.parentElement?.getAttribute('href'),
                          outerHTML: el.outerHTML.slice(0,300)});
            }
        });
        return out;
    }""")
    import json
    print(json.dumps(links, ensure_ascii=False, indent=2))
