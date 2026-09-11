from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222", timeout=60000)
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.goto("https://sis.liugong.com/tis/", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2500)
    print("URL:", page.url, "TITLE:", page.title())

    storage = page.evaluate("""() => {
        const ls = {}; for (let i=0;i<localStorage.length;i++){const k=localStorage.key(i); ls[k]=localStorage.getItem(k);}
        const ss = {}; for (let i=0;i<sessionStorage.length;i++){const k=sessionStorage.key(i); ss[k]=sessionStorage.getItem(k);}
        return {ls, ss};
    }""")
    with open("_recon/sis_storage.json","w",encoding="utf-8") as f:
        json.dump(storage, f, ensure_ascii=False, indent=2)
    print("localStorage keys:", list(storage["ls"].keys()))
    print("sessionStorage keys:", list(storage["ss"].keys()))

    state = ctx.storage_state()
    with open("session/storage_state.json","w",encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    for c in state["cookies"]:
        if "sis" in c["domain"]:
            print("cookie:", c["domain"], c["name"], "=", c["value"][:60])
    page.close()
