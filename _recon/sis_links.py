from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    page.wait_for_timeout(2000)
    page.screenshot(path="_recon/sis_links_portal.png", full_page=True)
    links = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('a').forEach(el => {
            const t = (el.textContent||'').trim();
            if (['SIS','EPC','EPC2'].includes(t)) {
                out.push({text: t, href: el.getAttribute('href'), onclick: el.getAttribute('onclick'),
                          id: el.id, outerHTML: el.outerHTML.slice(0,250)});
            }
        });
        return out;
    }""")
    print(json.dumps(links, ensure_ascii=False, indent=2))
