"""Mint a fresh epc.liugong.com JSESSIONID from an already-authenticated SSO
portal tab. Types no credentials -- it only clicks the EPC app icon and reads
the resulting cookies, so it works whenever the portal itself is still logged
in (the EPC app session dies hours before the SSO one does).
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from playwright.sync_api import sync_playwright

PORTAL = "https://ssoweb.liugong.com/jsp/custompage/0/usergateway/userapplist.jsp"

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=90000)
    ctx = b.contexts[0]

    # drop stale EPC tabs sitting on EPC's own login form
    for pg in list(ctx.pages):
        if "epc.liugong.com" in pg.url:
            try:
                pg.close()
            except Exception as e:
                print("close failed:", e)

    portal = None
    for pg in ctx.pages:
        if "userapplist.jsp" in pg.url:
            portal = pg
            break
    if portal is None:
        portal = ctx.new_page()
    portal.goto(PORTAL, wait_until="load", timeout=40000)
    portal.wait_for_timeout(2500)

    if portal.query_selector("input[type='password']"):
        print("PORTAL NEEDS LOGIN -- ask the user to sign in by hand")
        raise SystemExit(2)

    epc = None
    try:
        with ctx.expect_page(timeout=25000) as info:
            portal.click("text=EPC", timeout=10000)
        epc = info.value
    except Exception as e:
        print("no new tab from click:", type(e).__name__)
        for pg in ctx.pages:
            if "epc.liugong.com" in pg.url:
                epc = pg
                break
    if epc is None:
        print("EPC TAB NOT FOUND")
        raise SystemExit(3)

    try:
        epc.wait_for_load_state("load", timeout=40000)
    except Exception as e:
        print("load wait:", type(e).__name__)
    epc.wait_for_timeout(3000)
    print("EPC URL:", epc.url[:120])

    state = ctx.storage_state()
    sid = None
    for c in state["cookies"]:
        if c["domain"] == "epc.liugong.com" and c["name"] == "JSESSIONID":
            sid = c["value"]
    if not sid:
        print("NO JSESSIONID -- not saving")
        raise SystemExit(4)
    with open("session/storage_state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print("NEW epc JSESSIONID:", sid)
