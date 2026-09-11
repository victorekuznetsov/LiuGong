from playwright.sync_api import sync_playwright

URL = "https://ssoweb.liugong.com/jsp/custompage/0/usergateway/userapplist.jsp"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL, wait_until="networkidle", timeout=30000)
    print("TITLE:", page.title())
    print("URL:", page.url)
    page.screenshot(path="_recon/step1_login.png", full_page=True)
    html = page.content()
    with open("_recon/step1_login.html", "w", encoding="utf-8") as f:
        f.write(html)
    browser.close()
print("done")
