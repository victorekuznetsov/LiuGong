"""Shared HTTP layer for LiuGong SIS (Service Information System).

SIS is a plain REST API behind a Vue SPA -- no browser needed once you hold a
token. The SPA's interceptor sets BOTH `token` and `Authorization` to the raw
JWT (no "Bearer" prefix, which is why Authorization: Bearer ... returns 401),
plus Accept-Language. The JWT lives in the SPA's localStorage; grab it with
_recon/get_sis_token.py after clicking SIS on the SSO portal, which writes
session/sis_localstorage.json.

Endpoint names were recovered from the SPA bundle
(https://sis.liugong.com/tis/ -> assets/index.<hash>.js, ~12 MB, needs no
auth). The hash changes on redeploy, so re-fetch the page to find the current
filename and re-grep `url:"` call sites if something 404s.
"""
import json
import os
import time

import requests

BASE = "https://sis.liugong.com/api/tis"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(ROOT, "session", "sis_localstorage.json")


class TokenExpired(BaseException):
    """Same rationale as lg_api.SessionExpired: must not be swallowed by a
    per-item `except Exception`, so a dead token stops the run instead of
    writing thousands of error stubs."""


def token():
    with open(TOKEN_FILE, encoding="utf-8") as f:
        ls = json.load(f)
    for key in ("token", "Token", "access_token"):
        if isinstance(ls, dict) and ls.get(key):
            return ls[key]
    # localStorage dumps sometimes arrive as a list of {name,value} pairs
    if isinstance(ls, list):
        for item in ls:
            if item.get("name") in ("token", "Token", "access_token"):
                return item["value"]
    raise SystemExit(f"no token in {TOKEN_FILE} - re-run _recon/get_sis_token.py")


class Sis:
    def __init__(self, lang="en-US", tok=None):
        self.lang = lang
        self.token = tok or token()
        self.s = requests.Session()
        self.s.headers.update({
            "token": self.token,
            "Authorization": self.token,
            "Accept-Language": lang,
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
        })

    def _req(self, method, path, *, retries=4, raw=False, **kw):
        last = None
        for attempt in range(retries):
            try:
                r = self.s.request(method, BASE + path, timeout=180, **kw)
                if r.status_code == 200:
                    return r if raw else r.json()
                if r.status_code in (401, 403):
                    last = f"HTTP {r.status_code}"
                    if attempt == retries - 1:
                        raise TokenExpired(f"{method} {path} -> {r.status_code} "
                                           f"on all {retries} attempts")
                    time.sleep(2 * (attempt + 1))
                    continue
                last = f"HTTP {r.status_code}"
            except requests.RequestException as e:
                last = type(e).__name__
            time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"{method} {path} failed: {last}")

    def get(self, path, **params):
        return self._req("GET", path, params=params or None)

    def post(self, path, **body):
        return self._req("POST", path, json=body or None)

    # --- machine identity -------------------------------------------------
    def vin(self, vin):
        """-> {number,type,brand,modelCode,modelYear,driverType,serialNumber};
        driverType is the EPC material number, the join key to rawdata/."""
        return self.get("/rest/home/vin", vin=vin)

    def vehicle_info(self, **params):
        return self.get("/rest/Manual/getVehicleInfo", **params)

    # --- model hierarchy --------------------------------------------------
    def model_root(self, **params):
        return self.get("/rest/model/root", **params)

    def model_childs(self, **params):
        return self.get("/rest/model/childs", **params)

    def model_tree_by_code(self, code):
        return self.get("/rest/model/treeByCode", code=code)

    # --- manual trees (one per document family) ---------------------------
    MANUAL_KINDS = {
        "manual": ("/rest/manual/root", "/rest/manual/childs"),
        "user": ("/rest/user-manual/root", "/rest/user-manual/childs"),
        "circuit": ("/rest/circuit-manual/root", "/rest/circuit-manual/childs"),
        "lt": ("/rest/lt-manual/root", "/rest/lt-manual/childs"),
        "metal": ("/rest/metal-manual/root", None),
    }

    def manual_root(self, kind="manual", **params):
        return self.get(self.MANUAL_KINDS[kind][0], **params)

    def manual_childs(self, kind="manual", **params):
        path = self.MANUAL_KINDS[kind][1]
        if path is None:
            raise ValueError(f"{kind} has no childs endpoint")
        return self.get(path, **params)

    def manual_page(self, **params):
        return self.get("/rest/manual/page", **params)

    # --- search / bulletins ----------------------------------------------
    def global_search(self, keyword, **params):
        return self.get("/rest/home/globalSearch", keyword=keyword, **params)

    def topic_search(self, **params):
        return self.get("/rest/base/topic/search", **params)

    def bulletin_page(self, **params):
        return self.get("/rest/base/bulletin/page", **params)

    def bulletin(self, bid):
        return self.get(f"/rest/base/bulletin/{bid}")

    # --- download area ----------------------------------------------------
    def download_folder_tree(self, **params):
        return self.get("/rest/base/download/folder/tree", **params)

    def download_top_files(self, **params):
        return self.get("/rest/base/download/top-files", **params)

    # --- file bytes -------------------------------------------------------
    def file_view(self, file_id):
        """The SPA's own getFileViewUrl(): /rest/base/file/view/<id>."""
        return self._req("GET", f"/rest/base/file/view/{file_id}", raw=True)

    def file_download(self, file_id):
        return self._req("GET", f"/rest/base/file/download/{file_id}", raw=True)

    def file_resource(self, file_id):
        """Obfuscated variant the SPA uses for some resources: the path segment
        is base64(encodeURI("Ji32k7au4a83$d0g" + id)) -- salt lifted verbatim
        from the bundle."""
        import base64
        from urllib.parse import quote
        tok = base64.b64encode(
            quote(f"Ji32k7au4a83$d0g{file_id}", safe="!#$&'()*+,/:;=?@[]~")
            .encode()).decode()
        return self._req("GET", f"/rest/base/file/download/resource/{tok}", raw=True)


EXT_BY_CTYPE = {
    "application/pdf": "pdf",
    "application/zip": "zip",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "image/jpeg": "jpg",
    "image/png": "png",
    "text/html": "html",
    "application/octet-stream": "bin",
}


def save_file(path, resp):
    ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
    ext = EXT_BY_CTYPE.get(ctype, "bin")
    if not path.endswith("." + ext):
        path = f"{path}.{ext}"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "wb") as f:
        f.write(resp.content)
    os.replace(tmp, path)
    return path
