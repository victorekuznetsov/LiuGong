"""Сборка каталога LiuGong из выгрузки EPC.

    python3 tools/build_catalog.py                  все книги
    python3 tools/build_catalog.py 08F0096C011B002  одну
    KEEP_MEDIA=1 python3 tools/build_catalog.py     не перерисовывать чертежи
    python3 tools/build_catalog.py --trees          только деревья разделов

На выходе — тот же набор файлов, что у каталога Komatsu:

    books.js                     опись книг
    data/<книга>/tree.js         дерево разделов и узлов, без позиций
    data/<книга>/u/<узел>.js     состав узла и выноски чертежа
    data/index/parts-<XX>.js     номер детали -> где встречается, шардами
    data/names.js                китайские наименования (для переключателя языка)
    media/<книга>/<узел>.svg     чертёж

Строка позиции пишется массивом, а не объектом с именами полей: имена,
повторённые шестьдесят тысяч раз, весят больше самих данных.

    rows: [выноска, номер детали, наименование (EN), количество,
           примечание, рекомендация по запасу, ссылка на вложенный узел,
           признаки, кратность упаковки]
    spots: [выноска, x1, y1, x2, y2]

Хвостовые пустые поля обрезаются.
"""
import os
import re
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lgraw                                                   # noqa: E402
import svgopt                                                  # noqa: E402
from lgraw import ROOT, norm, legend_parts, eff_date           # noqa: E402

OUT = ROOT
KEEP_MEDIA = os.environ.get("KEEP_MEDIA") == "1"
# Только дерево: чертежи и состав узлов не трогаются. Пересборка дерева
# не требует разбора SVG и занимает секунды, а не полчаса, — пригождается,
# когда меняется раскладка дерева, а не сами данные.
TREES_ONLY = False

# Признаки позиции, битами: в строке они занимают одно число вместо девяти
# полей, которые почти всегда пустые.
F_KIT = 1        # ремкомплект
F_REMAN = 2      # восстановленная деталь (Reman)
F_PHOTO = 4      # есть фотография
F_SUPERS = 8     # есть цепочка замен
F_BULLETIN = 16  # есть бюллетень
F_FIT = 32       # отмечена в конфигурации машины (флаг EPC `checked`)
F_NOORDER = 64   # отдельно не поставляется

# Вид техники EPC пишет по-китайски, и таких значений на всю выгрузку
# ровно восемь. Переводить их машинно незачем — проще перечислить.
# Марка в EPC тоже с китайским хвостом исполнения: `CLG8128H康明斯T3` —
# это «CLG8128H, двигатель Cummins, Tier 3». В шапке каталога он не нужен,
# но и терять его нельзя: полная строка остаётся в паспорте книги.
KIND_RU = {
    "中型挖掘机": "экскаватор среднего класса",
    "大型挖掘机": "экскаватор тяжёлого класса",
    "轮胎式挖掘机": "колёсный экскаватор",
    "全液响单钢轮压路机": "полногидравлический одновальцовый каток",
    "全液压单钢轮压路机": "полногидравлический одновальцовый каток",
    "60型轮式装载机": "фронтальный погрузчик 60-й серии",
    "90及以上型轮式装载机": "фронтальный погрузчик 90-й серии и выше",
}
LINE_RU = {
    "挖掘机": "экскаваторы",
    "压路机": "катки",
    "轮式装载机": "фронтальные погрузчики",
}


def model_short(s):
    """`CLG8128H康明斯T3` -> `CLG8128H`: марка без китайского хвоста."""
    s = str(s or "").strip()
    m = re.match(r"^[\x20-\x7E]+", s)
    return (m.group(0).strip() if m else s) or s


def trim(row):
    while row and (row[-1] == "" or row[-1] == 0 or row[-1] is None):
        row.pop()
    return row


def unit_rows(code, legend, zh_names, sub_refs):
    """Состав узла: строки таблицы и китайские наименования на будущее."""
    en = lgraw.parts(code, legend, "en_US")
    zh = lgraw.parts(code, legend, "zh_CN")
    zh_by = {}
    for r in zh:
        zh_by[(str(r.get("callout")), r.get("partNO"))] = r.get("partName") or ""
    rows = []
    for r in en:
        part = (r.get("partNO") or "").strip()
        callout = str(r.get("callout") or "").strip()
        name = (r.get("partName") or "").strip()
        cn = zh_by.get((callout, part), "")
        if name and cn and cn != name:
            zh_names[name] = cn
        flags = 0
        if r.get("kit"):
            flags |= F_KIT
        if r.get("saleReman"):
            flags |= F_REMAN
        if r.get("havePartPicture"):
            flags |= F_PHOTO
        if r.get("haveSupersession"):
            flags |= F_SUPERS
        if r.get("haveBulletin"):
            flags |= F_BULLETIN
        if r.get("checked"):
            flags |= F_FIT
        if r.get("order") is False:
            flags |= F_NOORDER
        mpq = str(r.get("mpq") or "").strip()
        # У части позиций номера нет вовсе — вместо него EPC пишет, почему:
        # «ремонтируется в составе вышестоящей сборки». Это и есть
        # примечание к строке, терять его нельзя.
        note = (r.get("note") or "").strip()
        if not note:
            note = (r.get("serviceSupportType") or "").strip()
        rows.append(trim([
            callout,
            part,
            name,
            str(r.get("qty") or "").strip(),
            note,
            (r.get("storeTypeName") or "").strip(),
            part if part in sub_refs else "",
            flags,
            mpq if mpq not in ("", "1") else "",
        ]))
    return rows


def build_book(code, index, stats):
    """Одна книга: дерево, узлы, чертежи. Возвращает строку для books.js."""
    mach = lgraw.machine(code)
    legends = lgraw.legends(code)
    tree_en = lgraw.tree(code, "en_US")
    tree_zh = lgraw.tree(code, "zh_CN")
    zh_by_id = {}
    for n in lgraw.walk(tree_zh):
        zh_by_id[n.get("id")] = (n.get("name") or "").strip()

    # Номера сборок, у которых есть собственный чертёж: по ним в таблице
    # позиций появляется стрелка «открыть вложенный узел».
    sub_refs = set()
    for n in lgraw.walk(tree_en):
        if n.get("versions"):
            sub_refs.add((n.get("partNo") or "").strip())
    sub_refs.discard("")

    zh_names = {}
    media_dir = os.path.join(OUT, "media", code)
    unit_dir = os.path.join(OUT, "data", code, "u")
    os.makedirs(media_dir, exist_ok=True)
    os.makedirs(unit_dir, exist_ok=True)

    written, sheets, lines, spots_n = set(), 0, 0, 0
    numbers = set()

    def emit_unit(legend, node):
        """Файл узла и чертёж к нему. Возвращает, удалось ли."""
        nonlocal sheets, lines, spots_n
        if legend in written:
            return True
        if TREES_ONLY:
            written.add(legend)
            return True
        rows = unit_rows(code, legend, zh_names, sub_refs)
        callouts = set(r[0] for r in rows if r and r[0])
        svg_path = os.path.join(media_dir, legend + ".svg")
        w = h = 0.0
        spots = []
        src = lgraw.drawing(code, legend)
        if src is not None:
            if KEEP_MEDIA and os.path.exists(svg_path):
                # чертёж уже нарисован — выноски всё равно нужны, но
                # разбирать ради них исходник дешевле, чем писать файл
                out, w, h, spots = svgopt.optimize(src, callouts)
            else:
                out, w, h, spots = svgopt.optimize(src, callouts)
                with open(svg_path, "w", encoding="utf-8") as f:
                    f.write(out)
            sheets += 1
        lg = legends.get(legend) or {}
        page = {
            "id": legend,
            "t": (node.get("name") or lg.get("name") or legend).strip(),
            "r": (node.get("partNo") or "").strip(),
            "g": legend,
            "d": eff_date(lg.get("note")),
            "w": round(w, 1),
            "h": round(h, 1),
            "rows": rows,
            "spots": spots,
        }
        lgraw.write_data(os.path.join(unit_dir, legend + ".js"),
                         "u:%s/%s" % (code, legend), page)
        written.add(legend)
        lines += len(rows)
        spots_n += len(spots)
        for r in rows:
            if len(r) > 1 and r[1]:
                numbers.add(r[1])
                index[norm(r[1])].append([code, legend, r[0], r[1]])
        return True

    def node_entry(n, numbered=False):
        """Узел дерева: сам узел плюс вложенные и старые редакции чертежа.

        `numbered` — у сборки несколько листов, и нумеровать надо все, а
        не только со второго: иначе первый лист останется без номера и
        будет выглядеть как сама сборка.
        """
        vers = sorted(n.get("versions") or [],
                      key=lambda v: legend_parts(v.get("legendCode"))[1:],
                      reverse=True)
        name = (n.get("name") or "").strip()
        # У сборки бывает несколько листов, и EPC называет их одинаково:
        # три «Топливные системы» подряд. Номер листа приписывается к
        # названию, иначе в дереве их не различить.
        split = str(n.get("splitNo") or "").strip()
        if split and (numbered or split not in ("0", "00")):
            try:
                name += " · лист %d" % (int(split) + 1)
            except ValueError:
                name += " · лист " + split
        nid = n.get("id") or ""
        kids = []
        # старые редакции того же чертежа и дополнительные листы
        primary = None
        for i, v in enumerate(vers):
            lc = v.get("legendCode")
            if not lc:
                continue
            emit_unit(lc, n)
            if primary is None:
                primary = lc
            else:
                d = eff_date((legends.get(lc) or {}).get("note"))
                kids.append({"id": lc, "ref": (n.get("partNo") or "").strip(),
                             "title": name + (" · ред. " + d if d else " · ред."),
                             "g": 1, "d": d})
        children = n.get("children") or []
        # Несколько листов одной сборки: `60C6073_00`, `_01`, `_02`.
        sheets = sum(1 for c in children
                     if (c.get("partNo") or "").strip() == (n.get("partNo") or "").strip()
                     and c.get("versions"))
        for c in children:
            e = node_entry(c, numbered=sheets > 1)
            if e:
                kids.append(e)
        if primary is None and not kids:
            return None
        ref = (n.get("partNo") or "").strip()
        # В дереве EPC над узлом стоит ещё один, служебный: у сборки
        # `60C6073` сначала идёт узел `60C6073` без чертежа, и уже внутри
        # него — `60C6073_00` с чертежами. В каталоге это выглядело бы как
        # «Топливная система» внутри «Топливной системы». Если такой узел
        # ничего не несёт — ни чертежа, ни второго потомка — и потомок у
        # него той же сборки, показываем сразу потомка.
        if primary is None and len(kids) == 1 and kids[0].get("ref") == ref:
            kid = kids[0]
            if not kid.get("title"):
                kid["title"] = name
            return kid
        entry = {
            "id": primary or nid,
            "ref": ref,
            "title": name,
        }
        if primary:
            entry["g"] = 1
            d = eff_date((legends.get(primary) or {}).get("note"))
            if d:
                entry["d"] = d
        else:
            entry["n"] = 1            # группа без чертежа: только раскрывается
        if kids:
            entry["kids"] = kids
        if nid and zh_by_id.get(nid) and zh_by_id[nid] != name:
            zh_names[name] = zh_by_id[nid]
        return entry

    sections = []
    for sec in tree_en:
        kids = []
        for c in (sec.get("children") or []):
            e = node_entry(c)
            if e:
                kids.append(e)
        title = (sec.get("name") or sec.get("code") or "").strip()
        if not kids:
            # раздел без вложенных: сам может нести чертежи
            e = node_entry(sec)
            if not e:
                continue
            kids = e.get("kids") or [e]
        zid = sec.get("id")
        if zid and zh_by_id.get(zid) and zh_by_id[zid] != title:
            zh_names[title] = zh_by_id[zid]
        sections.append({"id": sec.get("code") or zid, "title": title, "kids": kids})

    lgraw.write_data(os.path.join(OUT, "data", code, "tree.js"),
                     "tree:" + code, sections)

    if TREES_ONLY:
        return None

    # чертежи, на которые никто не сослался (в описи есть, в дереве нет)
    orphans = [lc for lc in legends if lc not in written]
    for lc in orphans:
        lg = legends[lc]
        emit_unit(lc, {"name": lg.get("name"), "partNo": lg.get("partNo")})

    stats["zh"].update(zh_names)
    kind = (mach.get("machineType") or "").strip()
    line = (mach.get("productLine") or "").strip()
    sub = (mach.get("subModel") or code).strip()
    return {
        "code": code,
        "model": model_short(sub),
        "model_full": sub,
        "vin": (mach.get("vin") or "").strip(),
        "line": LINE_RU.get(line, line),
        "line_zh": line,
        "kind": KIND_RU.get(kind, kind),
        "kind_zh": kind,
        "spec": (mach.get("materialNo") or "").strip(),
        "graphics": "vector",
        "lang": "en",
        "units": len(written),
        "sheets": sheets,
        "lines": lines,
        "numbers": len(numbers),
        "spots": spots_n,
        "orphans": len(orphans),
    }


def main(argv):
    global TREES_ONLY
    t0 = time.time()
    want = [a for a in argv[1:] if not a.startswith("--")]
    TREES_ONLY = "--trees" in argv
    codes = [c for c in lgraw.books() if not want or c in want]
    if not codes:
        raise SystemExit("нет таких книг в выгрузке: " + ", ".join(want))
    index = defaultdict(list)
    stats = {"zh": {}}
    rows = []
    for code in codes:
        t = time.time()
        b = build_book(code, index, stats)
        if b is None:                      # --trees: переписано только дерево
            print("%-18s дерево пересобрано  %.1f с" % (code, time.time() - t), flush=True)
            continue
        rows.append(b)
        print("%-18s %5d узлов  %5d чертежей  %6d позиций  %5d номеров  %.0f с"
              % (code, b["units"], b["sheets"], b["lines"], b["numbers"], time.time() - t),
              flush=True)

    if TREES_ONLY:
        print("деревья пересобраны; books.js, индекс и чертежи не трогались")
        return
    if want:
        print("собраны не все книги — books.js и индекс не трогаем")
        return
    lgraw.write_global(os.path.join(OUT, "books.js"), "BOOKS", rows,
                       "Книги каталога. Пересобирается tools/build_catalog.py.")
    shards = defaultdict(dict)
    for no, hits in index.items():
        shards[no[:2] or "__"][no] = hits
    idx_dir = os.path.join(OUT, "data", "index")
    os.makedirs(idx_dir, exist_ok=True)
    for name in os.listdir(idx_dir):
        os.remove(os.path.join(idx_dir, name))
    for name, obj in shards.items():
        lgraw.write_data(os.path.join(idx_dir, "parts-%s.js" % name), "idx:" + name, obj)
    lgraw.write_data(os.path.join(OUT, "data", "names.js"), "zh", stats["zh"],
                     "Китайские наименования из выгрузки EPC. tools/build_catalog.py.")
    print("итого: %d книг, %d номеров, %d кусков индекса, %.0f с"
          % (len(rows), len(index), len(shards), time.time() - t0))


if __name__ == "__main__":
    main(sys.argv)
