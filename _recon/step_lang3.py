from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    res = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('a').forEach(a => {
            const h = a.getAttribute('href') || '';
            const oc = a.getAttribute('onclick') || '';
            const t = (a.textContent||'').trim();
            if (h.includes('lang') || oc.includes('lang') || /中文|English|русск|Deutsch|español|italiano|français|portugu/i.test(t)) {
                out.push({text: t, href: h, onclick: oc, id: a.id, cls: a.className});
            }
        });
        return out;
    }""")
    for r in res:
        print(r)
