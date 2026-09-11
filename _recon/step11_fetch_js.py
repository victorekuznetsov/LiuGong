from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9333")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    for name in ["group.js","parts.js","legend_new.js","main.js"]:
        txt = page.evaluate(f"""async () => {{
            const r = await fetch('/js/module/usage/{name}', {{credentials:'include'}});
            return await r.text();
        }}""")
        with open(f"_recon/js_{name}", "w", encoding="utf-8") as f:
            f.write(txt)
        print(name, len(txt))
