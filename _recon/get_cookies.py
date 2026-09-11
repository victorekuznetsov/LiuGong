from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    state = ctx.storage_state()
    with open("session/storage_state.json","w",encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    for c in state["cookies"]:
        print(c["domain"], c["name"], "=", c["value"][:40])
