"""Mirrors one LiuGong EPC machine catalog into rawdata/<modelCode>/.

    python tools/crawl_machine.py <VIN> [--only tree|parts|drawings|details|photos]

Everything is resumable: a file already on disk is never fetched twice, so the
script can just be re-run after an interruption or a session refresh.
"""
import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lg_api import BASE, Epc, save_svgz, walk_tree  # noqa: E402
import part_detail  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCALES = ("zh_CN", "en_US")
THREADS = 4

_print_lock = threading.Lock()


def log(*a):
    with _print_lock:
        print(*a, flush=True)


def jdump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{threading.get_ident()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


CRUMB_KEY = {
    "productCode": "productLine", "machineCode": "machineType",
    "submachineCode": "subModel", "modelCode": "materialNo",
}


def machine_meta(epc, vin):
    """Product line / model / material number, scraped off the machine page."""
    import re
    r = epc._req("GET", f"/usage/vin/{vin}")
    html = r.text
    meta = {"vin": vin}
    m = re.search(r'modelCode\s*:\s*"([^"]+)"', html)
    if m:
        meta["modelCode"] = m.group(1)
    m = re.search(r"crumbs\s*:\s*'(\[.*?\])'", html)
    if m:
        crumbs = json.loads(m.group(1).replace('\\"', '"'))
        for c in crumbs:
            key = CRUMB_KEY.get(c.get("type"))
            if key:
                meta[key] = c.get("text")
                meta[key + "Code"] = c.get("code")
    return meta, html


def collect_legends(tree):
    """legendCode -> {systemCode, nodeId, partNo, name, note, checked}."""
    out = {}
    for n in walk_tree(tree["result"]["data"]):
        for v in (n.get("versions") or []):
            out.setdefault(v["legendCode"], {
                "legendCode": v["legendCode"],
                "systemCode": n.get("systemCode"),
                "nodeId": n.get("id"),
                "partNo": n.get("partNo"),
                "name": v.get("name"),
                "note": v.get("note"),
                "checked": bool(n.get("checked")),
                "level": n.get("level"),
            })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vin")
    ap.add_argument("--only", choices=["tree", "parts", "drawings", "details", "photos"])
    ap.add_argument("--threads", type=int, default=THREADS)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    vin = args.vin
    steps = {args.only} if args.only else {"tree", "parts", "drawings", "details", "photos"}

    epc = {loc: Epc(locale=loc) for loc in LOCALES}
    meta, html = machine_meta(epc["zh_CN"], vin)
    model = meta.get("modelCode") or meta.get("materialNo", "").split("(")[0] or vin
    out = os.path.join(ROOT, "rawdata", model)
    os.makedirs(out, exist_ok=True)
    meta["crawledAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    jdump(os.path.join(out, "machine.json"), meta)
    log(f"machine {vin} -> {model}  {meta.get('subModel','')} {meta.get('productLine','')}")

    # --- tree (one per locale) -------------------------------------------
    trees = {}
    for loc in LOCALES:
        p = os.path.join(out, f"tree_{loc}.json")
        if os.path.exists(p):
            trees[loc] = json.load(open(p, encoding="utf-8"))
        else:
            trees[loc] = epc[loc].tree_vin(vin)
            jdump(p, trees[loc])
            log(f"  tree {loc}: saved")
    legends = collect_legends(trees["zh_CN"])
    jdump(os.path.join(out, "legends.json"), legends)
    log(f"  legends: {len(legends)} ({sum(1 for v in legends.values() if v['checked'])} on this VIN)")
    if steps == {"tree"}:
        return

    codes = sorted(legends, key=lambda c: (not legends[c]["checked"], c))
    if args.limit:
        codes = codes[:args.limit]

    # --- parts lists ------------------------------------------------------
    part_nos = set()
    if "parts" in steps:
        def do_parts(code):
            info = legends[code]
            got = 0
            for loc in LOCALES:
                p = os.path.join(out, "parts", loc, code + ".json")
                if os.path.exists(p):
                    data = json.load(open(p, encoding="utf-8"))
                else:
                    j = epc[loc].parts(vin, model, info["systemCode"] or "", code)
                    data = (j.get("result") or {}).get("data") or []
                    jdump(p, data)
                got = len(data)
                if loc == "zh_CN":
                    for d in data:
                        if d.get("partNO"):  # can be None: not sold separately,
                            part_nos.add((d["partNO"], str(d.get("parentPartNO") or "")))
            return code, got

        with ThreadPoolExecutor(args.threads) as ex:
            for i, (code, n) in enumerate(ex.map(do_parts, codes), 1):
                if i % 25 == 0 or n == 0:
                    log(f"  parts {i}/{len(codes)} {code} n={n}")
        log(f"  parts done: {len(part_nos)} unique part numbers")
        jdump(os.path.join(out, "part_index.json"), sorted(part_nos))
    else:
        idx = os.path.join(out, "part_index.json")
        if os.path.exists(idx):
            part_nos = {tuple(x) for x in json.load(open(idx, encoding="utf-8"))}

    # --- drawings ---------------------------------------------------------
    if "drawings" in steps:
        os.makedirs(os.path.join(out, "drawings"), exist_ok=True)

        def do_svg(code):
            p = os.path.join(out, "drawings", code + ".svgz")
            if os.path.exists(p) and os.path.getsize(p) > 0:
                return code, -1
            try:
                svg = epc["zh_CN"].legend_svg(code, vin)
            except Exception as e:
                log(f"  ! svg {code}: {e}")
                return code, 0
            save_svgz(p, svg)
            return code, os.path.getsize(p)

        with ThreadPoolExecutor(min(args.threads, 3)) as ex:
            for i, (code, sz) in enumerate(ex.map(do_svg, codes), 1):
                if i % 25 == 0:
                    log(f"  drawings {i}/{len(codes)}")
        log("  drawings done")

    # --- part details + supersession + photos ------------------------------
    # The part-photo <img src> is an obfuscated, session-scoped token with no
    # file extension (the human-readable filename only exists in a dead HTML
    # comment next to it). All locale sessions share the SAME JSESSIONID (only
    # the LOCALE cookie differs), so it's really one server-side session --
    # concurrent threads fetching other parts in between invalidate a token
    # before it's used. photo_lock forces "load part page -> grab its photos"
    # to run as one atomic step server-side, even with multiple worker threads.
    EXT_BY_CTYPE = {"image/jpeg": "jpg", "image/png": "png", "image/gif": "gif",
                    "image/bmp": "bmp", "image/webp": "webp"}
    photo_lock = threading.Lock()

    if ("details" in steps or "photos" in steps) and part_nos:
        first_parent = {}
        for pn, parent in sorted(part_nos):
            first_parent.setdefault(pn, parent)
        todo = sorted(first_parent.items())

        def fetch_photos(pn, loc, urls, seen, seq):
            """Downloads one locale's photo tokens for a part, right after
            fetching the page that issued them. `seen`/`seq` are threaded
            through across the two locale calls so numbering stays unique
            and stable across both, without re-scanning the same URL twice."""
            photo_dir = os.path.join(out, "photos", pn)
            have = {f.split(".")[0] for f in os.listdir(photo_dir)} if os.path.isdir(photo_dir) else set()
            for u in urls or []:
                if "nopic" in u or "." in u.rsplit("/", 1)[-1] or u in seen:
                    continue
                seen.add(u)
                seq += 1
                if f"{seq:02d}" in have:
                    continue
                try:
                    r = epc[loc]._req("GET", u, retries=2,
                                      headers={"Referer": f"{BASE}/part/{pn}/"})
                except Exception as e:
                    log(f"  ! photo {pn}#{seq}: {e}")
                    continue
                ext = EXT_BY_CTYPE.get((r.headers.get("Content-Type") or "").split(";")[0].strip(), "jpg")
                os.makedirs(photo_dir, exist_ok=True)
                with open(os.path.join(photo_dir, f"{seq:02d}.{ext}"), "wb") as f:
                    f.write(r.content)
            return seen, seq

        def do_detail(item):
            pn, parent = item
            p = os.path.join(out, "partinfo", f"{pn}.json")
            photo_dir = os.path.join(out, "photos", pn)
            need_detail = not os.path.exists(p)
            if need_detail:
                rec = {"partNO": pn, "parentPartNO": parent, "locales": {}}
                seen, seq = set(), 0
                for loc in LOCALES:
                    with photo_lock:  # detail fetch + its photo tokens must be atomic
                        try:
                            r = epc[loc]._req("GET", f"/part/{pn}/{parent or '&'}",
                                              headers={"Referer": f"{BASE}/usage/vin/{vin}"})
                            rec["locales"][loc] = part_detail.parse(r.text)
                        except Exception as e:
                            rec["locales"][loc] = {"error": str(e)}
                            continue
                        seen, seq = fetch_photos(pn, loc, rec["locales"][loc].get("photos"), seen, seq)
                try:
                    j = epc["zh_CN"]._req("POST", "/supersession/detail",
                                          data={"partNO": pn},
                                          headers={"Referer": f"{BASE}/usage/vin/{vin}"}).json()
                    rec["supersession"] = (j.get("result") or {}).get("data")
                except Exception as e:
                    rec["supersession"] = {"error": str(e)}
                jdump(p, rec)
                return pn, 1
            elif "photos" in steps and not os.path.isdir(photo_dir):
                # details already on disk, but its photo tokens are stale by
                # now -> re-fetch the live page just to get fresh tokens
                seen, seq = set(), 0
                for loc in LOCALES:
                    with photo_lock:
                        try:
                            r = epc[loc]._req("GET", f"/part/{pn}/{parent or '&'}",
                                              headers={"Referer": f"{BASE}/usage/vin/{vin}"})
                            photos = part_detail.parse(r.text).get("photos")
                        except Exception as e:
                            log(f"  ! refetch {pn}: {e}")
                            continue
                        seen, seq = fetch_photos(pn, loc, photos, seen, seq)
                return pn, 2
            return pn, -1

        with ThreadPoolExecutor(args.threads) as ex:
            for i, (pn, st) in enumerate(ex.map(do_detail, todo), 1):
                if i % 50 == 0:
                    log(f"  details+photos {i}/{len(todo)}")
        log("  details+photos done")


if __name__ == "__main__":
    main()
