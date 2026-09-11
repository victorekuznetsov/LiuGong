from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222", timeout=90000)
    ctx = browser.contexts[0]
    portal = None
    for pg in ctx.pages:
        if "userapplist.jsp" in pg.url:
            portal = pg
            break
    if portal is None:
        portal = ctx.new_page()
        portal.goto("https://ssoweb.liugong.com/jsp/custompage/0/usergateway/userapplist.jsp", wait_until="load", timeout=30000)
        portal.wait_for_timeout(2000)

    with ctx.expect_page(timeout=20000) as newpage_info:
        portal.click("text=EPC", timeout=10000)
    newpage = newpage_info.value
    newpage.wait_for_load_state("load", timeout=30000)
    newpage.wait_for_timeout(2000)
    print("EPC URL:", newpage.url, "TITLE:", newpage.title())

    state = ctx.storage_state()
    with open("session/storage_state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    for c in state["cookies"]:
        if c["domain"] == "epc.liugong.com" and c["name"] == "JSESSIONID":
            print("NEW epc JSESSIONID:", c["value"])
