from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222", timeout=60000)
    ctx = browser.contexts[0]
    sis_page = None
    for pg in ctx.pages:
        if "sis.liugong.com" in pg.url:
            sis_page = pg
            break
    if sis_page is None:
        sis_page = ctx.new_page()
        sis_page.goto("https://sis.liugong.com/tis/#/home", wait_until="domcontentloaded", timeout=20000)
        sis_page.wait_for_timeout(1500)

    ls = sis_page.evaluate("""() => {
        const out = {};
        for (let i=0;i<localStorage.length;i++){const k=localStorage.key(i); out[k]=localStorage.getItem(k);}
        return out;
    }""")
    with open("session/sis_localstorage.json", "w", encoding="utf-8") as f:
        json.dump(ls, f, ensure_ascii=False, indent=2)
    print("keys:", list(ls.keys()))
