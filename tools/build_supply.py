"""Снабжение каталога LiuGong: цены и цепочки замен.

    python3 tools/build_supply.py          (после build_catalog.py)

Пишет `data/supply/s-<XX>.js` — шардами по первым двум знакам номера, как
поисковый индекс, — `data/supply/meta.json` и `codes.js` с расшифровкой
пометок о замене.

**Цены** берутся из прайс-листа «Люгонг … два базиса»: два столбца на два
базиса поставки. В прайсе номера набраны вперемешку латиницей и
кириллицей (`44С2104` и `44C2104` на вид одинаковы), поэтому сверка идёт
по приведённому номеру — иначе половина цен к каталогу не привязывается.

**Цепочки замен** в выгрузке EPC отдельным полем не приходят: раздел
`supersession` пуст у всех девятнадцати тысяч паспортов выгрузки. Но замена
записана словами в примечании к позиции — `CHANGE TO 71C4156 . ONE-WAY
REPLACEMENT`, `CHANGED FROM SP139575`, `INTERCHANGEABLE WITH 37B0119`, — и
разбирается оттуда.

Номер в примечании принимается, только если он есть в самом каталоге.
Выдёргивать «похожее на номер» регулярным выражением нельзя: в этих же
строках стоят `ONE-WAY`, `P/N`, `EXCAVATOR`, и половина из них прошла бы
как артикул.
"""
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lgraw                                       # noqa: E402
from lgraw import ROOT, norm                       # noqa: E402

PRICE_XLSX = os.path.join(ROOT, "Прайс-лист Люгонг 15.12.2025 два базиса.xlsx")

# Расшифровка пометок EPC. Ключи — наши, короткие; текст — для карточки
# детали в каталоге.
CODES = {
    "new": {"s": "заменена на", "f": "деталь снята с выпуска, вместо неё поставляется указанная"},
    "old": {"s": "заменяет", "f": "эта деталь пришла на смену указанной"},
    "both": {"s": "взаимозаменяема с", "f": "взаимозаменяемы в обе стороны"},
    "one": {"s": "односторонняя замена", "f": "новая ставится вместо старой, обратно — нет"},
    "up": {"s": "только в составе сборки", "f": "отдельно не поставляется, заказывается вышестоящая сборка"},
    "off": {"s": "снята с производства", "f": "поставка прекращена"},
    "na": {"s": "нет в поставке", "f": "недоступна к заказу"},
    "dup": {"s": "повторяющийся номер", "f": "номер встречается дважды, действует указанный"},
    "use": {"s": "применять", "f": "применять указанную деталь"},
}

RE_FROM = re.compile(r"CHANGED?\s+FROM\s+", re.I)
RE_TO = re.compile(r"CHANGED?\s+TO(?:\s+USE)?(?:\s+THE)?(?:\s+ITS\s+SUPERIOR\s+PART)?\s*", re.I)
RE_INTER = re.compile(r"INTERCHANGEABLE\s+WITH\s+", re.I)
RE_USE = re.compile(r"\bUSE\s+", re.I)
RE_TOKEN = re.compile(r"[0-9A-Za-z][0-9A-Za-z\-/]{4,}")
# Как выглядит артикул LiuGong. Выведено по 19 473 номерам самой выгрузки:
# `12B0428`, `00A0761X1`, `20C3426P02`, `SP139575`. Английские слова из
# примечаний (`SUPERIOR`, `ASSEMBLY`, `SUBPART`) под него не подходят.
RE_PART = re.compile(r"^(?:\d{2}[A-Z]\d{4}[0-9A-Z]{0,6}"
                     r"|[A-Z]{2}\d{6}[0-9A-Z]{0,4}"
                     r"|\d{9})$")


def numbers_in(text, known):
    """Артикулы из текста: [(номер, есть ли он в каталоге), …].

    Брать всё, что похоже на слово, нельзя: в этих же строках стоят
    `ONE-WAY`, `SUPERIOR PART`, `ASSEMBLY`. Поэтому берутся либо номера,
    которые есть в самом каталоге, либо строки, подходящие под шаблон
    артикула LiuGong. Второе нужно: завод часто заменяет деталь на номер,
    которого в наших восьми книгах нет, и молча выбрасывать такую замену
    хуже, чем показать её с пометкой «в этом каталоге нет».
    """
    out, seen = [], set()
    for m in RE_TOKEN.finditer(text or ""):
        k = norm(m.group())
        if k in seen:
            continue
        if k in known:
            seen.add(k)
            out.append((k, True))
        elif RE_PART.match(k):
            seen.add(k)
            out.append((k, False))
    return out


def parse_note(note, known, self_key):
    """Пометка EPC -> список звеньев цепочки замен и общий признак."""
    if not note:
        return [], ""
    t = note.strip()
    up = t.upper()
    links, flag = [], ""
    if "NOT FOR SALE AS PARTS" in up or "SUPERIOR PART" in up:
        flag = "up"
    elif "DISCONTINU" in up:
        flag = "off"
    elif "UNAVAILABLE" in up:
        flag = "na"
    elif "REPEATED P/N" in up:
        flag = "dup"

    two_way = ("TWO-WAY" in up or "INTERCHANGEABLE" in up) and "ONE-WAY" not in up
    one_way = "ONE-WAY" in up or "NOT THE OTHER WAY" in up

    def add(nos, direction, code):
        for n, inside in nos:
            if n == self_key:
                continue
            if not any(l["n"] == n for l in links):
                rec = {"n": n, "dir": direction, "code": code}
                if not inside:
                    rec["x"] = 1        # номера нет ни в одной из книг каталога
                links.append(rec)

    for m in RE_FROM.finditer(t):
        add(numbers_in(t[m.end():m.end() + 40], known), "old", "old")
    for m in RE_TO.finditer(t):
        add(numbers_in(t[m.end():m.end() + 40], known), "new",
            "one" if one_way else ("both" if two_way else "new"))
    for m in RE_INTER.finditer(t):
        add(numbers_in(t[m.end():m.end() + 40], known), "both", "both")
    if not links and RE_USE.search(t):
        m = RE_USE.search(t)
        add(numbers_in(t[m.end():m.end() + 40], known), "both", "use")
    return links, flag


def read_prices():
    """{приведённый номер: (цена базис 1, цена базис 2, наименование)}."""
    import openpyxl
    if not os.path.exists(PRICE_XLSX):
        return {}, ""
    wb = openpyxl.load_workbook(PRICE_XLSX, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    out = {}
    for row in ws.iter_rows(values_only=True):
        no = str(row[1] or "").strip()
        if not no or no == "Номер":
            continue
        key = norm(no)
        if not key:
            continue
        try:
            p1 = round(float(row[3]), 2) if row[3] not in (None, "") else None
            p2 = round(float(row[4]), 2) if row[4] not in (None, "") else None
        except (TypeError, ValueError):
            continue
        name = str(row[2] or "").strip()
        old = out.get(key)
        # один и тот же номер в прайсе встречается по многу раз; берём
        # первую строку с ценой и не затираем её пустыми повторами
        if old and old[0] is not None:
            continue
        out[key] = (p1, p2, name)
    wb.close()
    return out, os.path.basename(PRICE_XLSX)


def main():
    known = set()
    notes = {}          # приведённый номер -> {текст примечания}
    display = {}        # приведённый номер -> как он написан в каталоге
    for code in lgraw.books():
        for legend in lgraw.legends(code):
            for r in lgraw.parts(code, legend, "en_US"):
                part = (r.get("partNO") or "").strip()
                if not part:
                    continue
                k = norm(part)
                known.add(k)
                display.setdefault(k, part)
                n = (r.get("note") or "").strip()
                if n:
                    notes.setdefault(k, set()).add(n)

    prices, price_src = read_prices()

    supply = {}
    chains = 0
    for k, texts in notes.items():
        links, flags = [], []
        for t in sorted(texts):
            ls, f = parse_note(t, known, k)
            for l in ls:
                if not any(x["n"] == l["n"] for x in links):
                    l = dict(l)
                    l["d"] = display.get(l["n"], l["n"])
                    links.append(l)
            if f and f not in flags:
                flags.append(f)
        if links or flags:
            rec = supply.setdefault(display[k], {})
            if links:
                rec["c"] = links
                chains += len(links)
            if flags:
                rec["f"] = flags
            rec["note"] = sorted(texts)[0]

    priced = 0
    for k, (p1, p2, name) in prices.items():
        if k not in display:
            continue
        rec = supply.setdefault(display[k], {})
        p = {}
        if p1 is not None:
            p["b1"] = p1
        if p2 is not None:
            p["b2"] = p2
        if name:
            p["n"] = name
        if p:
            rec["p"] = p
            priced += 1

    shards = defaultdict(dict)
    for part, rec in supply.items():
        shards[norm(part)[:2] or "__"][part] = rec
    out_dir = os.path.join(ROOT, "data", "supply")
    if os.path.isdir(out_dir):
        for n in os.listdir(out_dir):
            os.remove(os.path.join(out_dir, n))
    os.makedirs(out_dir, exist_ok=True)
    for name, obj in shards.items():
        lgraw.write_data(os.path.join(out_dir, "s-%s.js" % name), "sup:" + name, obj)

    lgraw.write_global(os.path.join(ROOT, "codes.js"), "CODES", CODES,
                       "Расшифровка пометок о замене. tools/build_supply.py.")
    meta = {
        "numbers": len(known),
        "covered": len(supply),
        "priced": priced,
        "price_rows": len(prices),
        "chains": chains,
        "notes": len(notes),
        "sources": {"price": price_src},
    }
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    # то же самое, но как `.js`: с диска (`file://`) браузер `.json` не отдаёт
    lgraw.write_global(os.path.join(out_dir, "meta.js"), "SUPPLY_META", meta,
                       "Покрытие снабжения. tools/build_supply.py.")
    print("номеров в каталоге %d; с ценой %d из %d строк прайса; "
          "с пометкой о замене %d, звеньев %d; кусков %d"
          % (len(known), priced, len(prices), len(notes), chains, len(shards)))


if __name__ == "__main__":
    main()
