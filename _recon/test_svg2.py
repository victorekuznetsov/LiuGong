import requests

JSESSIONID = "fab784d6-e392-4053-af76-b2a969bd0a45"
BASE = "http://epc.liugong.com:800"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"

s = requests.Session()
s.cookies.set("JSESSIONID", JSESSIONID, domain="epc.liugong.com")
r = s.get(BASE + "/usage/legend-file",
          params={"url":"liugongsbomfile/legend/svg_audit/60C6073_003_00.svg"},
          headers={"User-Agent": UA, "Referer": BASE + "/usage/vin/LGC9125FARC135673"},
          timeout=180)
content = r.content
print("status", r.status_code, "bytes", len(content))
print("headers:", dict(r.headers))
print("ends with:", content[-200:].decode("utf-8","replace"))
open("_recon/sample_legend.svg","wb").write(content)
