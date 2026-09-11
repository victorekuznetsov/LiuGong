import requests, json

JSESSIONID = "fab784d6-e392-4053-af76-b2a969bd0a45"
BASE = "http://epc.liugong.com:800"
LOCALE_COOKIE = "org.springframework.web.servlet.i18n.CookieLocaleResolver.LOCALE"

def fetch_parts(locale):
    s = requests.Session()
    s.cookies.set("JSESSIONID", JSESSIONID, domain="epc.liugong.com")
    s.cookies.set(LOCALE_COOKIE, locale, domain="epc.liugong.com")
    r = s.post(BASE + "/usage/parts",
               data={"vin":"LGC9125FARC135673","modelCode":"08F0096C011B002",
                     "systemCode":"Y05","legendCode":"60C6073_003_00","parentPartNo":""},
               headers={"X-Requested-With":"XMLHttpRequest",
                        "Referer": BASE + "/usage/vin/LGC9125FARC135673",
                        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"},
               timeout=60)
    return r

for loc in ["zh_CN", "ru", "ru_RU", "en", "en_US"]:
    r = fetch_parts(loc)
    try:
        j = r.json()
        data = (j.get("result") or {}).get("data") or []
        names = [d["partName"] for d in data[:4]]
        print(loc, "->", r.status_code, "n=", len(data), names)
    except Exception as e:
        print(loc, "->", r.status_code, "ERR", str(e)[:100], r.text[:200])
