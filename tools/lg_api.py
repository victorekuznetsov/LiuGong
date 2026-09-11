"""Shared HTTP layer for the LiuGong EPC crawler.

Session cookies come from session/storage_state.json, written by tools/login.py
(a real Chrome session driven over CDP — the WAF blocks headless).
"""
import gzip
import json
import os
import re
import time

import requests

BASE = "http://epc.liugong.com:800"
LOCALE_COOKIE = "org.springframework.web.servlet.i18n.CookieLocaleResolver.LOCALE"
SVG_FTP_PATH = "liugongsbomfile/legend/svg_audit/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36")

class SessionExpired(BaseException):
    """Not an Exception subclass on purpose: crawl_machine.py's per-item
    `except Exception` handlers must NOT swallow this -- a 401 means the
    whole session is dead, so the entire run should stop immediately
    instead of grinding through thousands of doomed retries."""


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "session", "storage_state.json")

# Illustrator dumps its proprietary editing data into the SVG as one huge
# base64 CDATA blob; dropping it shrinks a drawing ~10x with no visual loss.
PGF_RE = re.compile(r"<i:pgf[ >].*?</i:pgf>", re.DOTALL)


def jsessionid():
    with open(STATE, encoding="utf-8") as f:
        state = json.load(f)
    for c in state["cookies"]:
        if c["name"] == "JSESSIONID" and c["domain"] == "epc.liugong.com":
            return c["value"]
    raise SystemExit("no epc.liugong.com JSESSIONID in session state - run tools/login.py")


class Epc:
    def __init__(self, locale="zh_CN", sid=None):
        self.locale = locale
        self.sid = sid or jsessionid()
        self.s = requests.Session()
        self.s.cookies.set("JSESSIONID", self.sid, domain="epc.liugong.com")
        self.s.cookies.set(LOCALE_COOKIE, locale, domain="epc.liugong.com")
        self.s.headers.update({
            "User-Agent": UA,
            "X-Requested-With": "XMLHttpRequest",
            "Accept-Encoding": "gzip, deflate",
        })

    def _req(self, method, path, *, retries=4, **kw):
        last = None
        for attempt in range(retries):
            try:
                r = self.s.request(method, BASE + path, timeout=180, **kw)
                if r.status_code == 200:
                    return r
                if r.status_code == 401:
                    # session is dead -- retrying just burns time, bail now
                    raise SessionExpired(f"{method} {path} -> 401 (session expired)")
                last = f"HTTP {r.status_code}"
            except requests.RequestException as e:
                last = type(e).__name__
            time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"{method} {path} failed: {last}")

    def tree_vin(self, vin):
        r = self._req("POST", "/legend-usage-group/tree/vin/",
                      data={"vin": vin},
                      headers={"Referer": f"{BASE}/usage/vin/{vin}"})
        return r.json()

    def tree_model(self, model_code):
        r = self._req("POST", "/legend-usage-group/tree",
                      data={"modelCode": model_code},
                      headers={"Referer": f"{BASE}/usage/{model_code}"})
        return r.json()

    def parts(self, vin, model_code, system_code, legend_code, parent_part_no=""):
        r = self._req("POST", "/usage/parts",
                      data={"vin": vin, "modelCode": model_code,
                            "systemCode": system_code, "legendCode": legend_code,
                            "parentPartNo": parent_part_no},
                      headers={"Referer": f"{BASE}/usage/vin/{vin}"})
        return r.json()

    def legend_svg(self, legend_code, vin=""):
        """Returns the drawing SVG with the Illustrator blob stripped."""
        r = self._req("GET", "/usage/legend-file",
                      params={"url": f"{SVG_FTP_PATH}{legend_code}.svg"},
                      headers={"Referer": f"{BASE}/usage/vin/{vin}"})
        svg = r.content.decode("utf-8", "replace")
        return PGF_RE.sub("", svg)


def save_svgz(path, svg_text):
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=6) as f:
        f.write(svg_text)


def walk_tree(nodes):
    for n in nodes:
        yield n
        yield from walk_tree(n.get("children") or [])
