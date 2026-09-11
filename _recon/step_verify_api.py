from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]

    parts = page.evaluate("""async () => {
        const r = await fetch('/usage/parts', {
            method:'POST',
            headers:{'Content-Type':'application/x-www-form-urlencoded;charset=UTF-8'},
            body:'vin=LGC9125FARC135673&modelCode=08F0096C011B002&systemCode=Y05&legendCode=60C6073_003_00&parentPartNo=',
            credentials:'include'});
        return await r.text();
    }""")
    with open("_recon/parts_ok.json","w",encoding="utf-8") as f:
        f.write(parts)
    print("PARTS len:", len(parts))
    print(parts[:1200])

    svg = page.evaluate("""async () => {
        const r = await fetch('/usage/legend-file?url=liugongsbomfile/legend/svg_audit/60C6073_003_00.svg', {credentials:'include'});
        return {status: r.status, len: (await r.text()).length};
    }""")
    print("SVG:", svg)
