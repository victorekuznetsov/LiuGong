import requests

JSESSIONID = "fab784d6-e392-4053-af76-b2a969bd0a45"
BASE = "http://epc.liugong.com:800"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"

s = requests.Session()
s.cookies.set("JSESSIONID", JSESSIONID, domain="epc.liugong.com")
r = s.get(BASE + "/usage/legend-file",
          params={"url":"liugongsbomfile/legend/svg_audit/60C6073_003_00.svg"},
          headers={"User-Agent": UA, "Referer": BASE + "/usage/vin/LGC9125FARC135673"},
          timeout=120, stream=True)
print("status", r.status_code, "ctype", r.headers.get("Content-Type"), "clen", r.headers.get("Content-Length"))
chunk = next(r.iter_content(4000)).decode("utf-8", "replace")
print(chunk[:1500])
total = len(chunk)
for c in r.iter_content(1024*256):
    total += len(c)
print("TOTAL BYTES:", total)
