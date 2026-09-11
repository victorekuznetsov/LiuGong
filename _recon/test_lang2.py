import requests, time

JSESSIONID = "fab784d6-e392-4053-af76-b2a969bd0a45"
BASE = "http://epc.liugong.com:800"
LOCALE_COOKIE = "org.springframework.web.servlet.i18n.CookieLocaleResolver.LOCALE"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"

def try_locale(locale, retries=2):
    for attempt in range(retries):
        try:
            s = requests.Session()
            s.cookies.set("JSESSIONID", JSESSIONID, domain="epc.liugong.com")
            s.cookies.set(LOCALE_COOKIE, locale, domain="epc.liugong.com")
            r = s.post(BASE + "/usage/parts",
                       data={"vin":"LGC9125FARC135673","modelCode":"08F0096C011B002",
                             "systemCode":"Y05","legendCode":"60C6073_003_00","parentPartNo":""},
                       headers={"X-Requested-With":"XMLHttpRequest",
                                "Referer": BASE + "/usage/vin/LGC9125FARC135673",
                                "User-Agent": UA, "Connection":"close"},
                       timeout=60)
            j = r.json()
            data = (j.get("result") or {}).get("data") or []
            return f"{locale} -> {r.status_code} n={len(data)} " + str([d['partName'] for d in data[:4]])
        except Exception as e:
            if attempt == retries - 1:
                return f"{locale} -> FAIL {type(e).__name__}"
            time.sleep(3)

for loc in ["ru_RU", "ru", "en_US", "en"]:
    print(try_locale(loc), flush=True)
    time.sleep(2)
