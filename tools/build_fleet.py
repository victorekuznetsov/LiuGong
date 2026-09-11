"""Парк LiuGong АО «Полюс» и привязка машин к книгам каталога.

    python3 tools/build_fleet.py          (после build_catalog.py)

Читает лист `PM-06` выгрузки `Liugong Fleet-КТГ.xlsx` и пишет `fleet.js`.

Привязка машины к книге у LiuGong устроена иначе, чем у Komatsu. Книга
Komatsu сделана на диапазон заводских номеров; книга LiuGong — на
конкретное исполнение (`materialNo`), и в EPC она открывается по VIN
машины. Поэтому у машины может быть три положения:

    vin    книга выкачана ровно по её VIN — состав точный;
    model  книга той же модели, но по VIN другой машины: исполнения
           совпадают не всегда, и это надо видеть, а не замалчивать;
    none   книги нет вовсе.

Молча приравнивать `model` к `vin` нельзя: по каталогу закажут не ту
деталь.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lgraw                                       # noqa: E402
from lgraw import ROOT                             # noqa: E402

FLEET_XLSX = os.path.join(ROOT, "Liugong Fleet-КТГ.xlsx")
SHEET = "PM-06"
MAKER = "LiuGong"

COL = {                      # номер столбца на листе -> поле
    1: "be", 3: "mvz", 4: "status", 5: "cls", 6: "maker", 7: "eo",
    8: "name", 9: "year", 10: "garage", 11: "sn", 12: "start",
    13: "model", 17: "retire", 20: "ktg",
}


def model_key(s):
    """`CLG8128H康明斯T3`, `8128H` -> `8128H`: общий вид марки.

    В EPC к марке приписано исполнение по-китайски: `CLG8128H康明斯T3` —
    это «CLG8128H, двигатель Cummins, Tier 3». Иероглифы выкинуть мало:
    после них остаётся `T3`, и марка `8128H` превращается в `8128HT3`,
    которой в парке нет. Поэтому строка режется по первому же незападному
    знаку, а уже потом чистится.
    """
    s = str(s or "")
    m = re.match(r"^[\x20-\x7E]*", s)
    s = re.sub(r"[^0-9A-Za-z]", "", m.group(0) if m else s).upper()
    return re.sub(r"^CLG", "", s)


def read_fleet():
    import openpyxl
    wb = openpyxl.load_workbook(FLEET_XLSX, read_only=True, data_only=True)
    ws = wb[SHEET]
    out = []
    for row in ws.iter_rows(values_only=True):
        cells = list(row) + [None] * 24
        if str(cells[6] or "").strip() != MAKER:
            continue
        m = {}
        for i, key in COL.items():
            v = cells[i]
            m[key] = ("" if v is None else str(v)).strip()
        if not m["eo"]:
            continue
        try:
            m["ktg"] = round(float(m["ktg"]), 3) if m["ktg"] else ""
        except ValueError:
            m["ktg"] = ""
        out.append(m)
    wb.close()
    return out


def main():
    books = json.loads(re.search(
        r"window\.BOOKS\s*=\s*(\[.*\]);", open(os.path.join(ROOT, "books.js"),
                                               encoding="utf-8").read(), re.S).group(1))
    by_vin, by_model = {}, {}
    for b in books:
        if b.get("vin"):
            by_vin[b["vin"].upper()] = b["code"]
        by_model.setdefault(model_key(b.get("model")), []).append(b["code"])

    fleet = read_fleet()
    counts = {"vin": 0, "model": 0, "none": 0}
    for m in fleet:
        sn = m["sn"].upper()
        if sn and sn in by_vin:
            m["books"] = [by_vin[sn]]
            m["fit"] = "vin"
        else:
            codes = by_model.get(model_key(m["model"]), [])
            m["books"] = list(codes)
            m["fit"] = "model" if codes else "none"
        counts[m["fit"]] += 1
        if m["sn"] == "#":
            m["sn"] = ""

    lgraw.write_global(os.path.join(ROOT, "fleet.js"), "FLEET", fleet,
                       "Парк LiuGong АО «Полюс». Пересобирается tools/build_fleet.py.")
    print("машин %d: по VIN %d, по модели %d, без книги %d"
          % (len(fleet), counts["vin"], counts["model"], counts["none"]))
    missing = sorted({m["model"] for m in fleet if m["fit"] == "none"})
    if missing:
        print("моделей без книги: " + ", ".join(missing))


if __name__ == "__main__":
    main()
