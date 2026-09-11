"""Хранилище Obsidian по базе знаний LiuGong.

    python3 tools/build_vault.py           (после build_kb.py)

Сделано по образцу хранилища Cummins (`obsidian-vault/` в
Cummins_Parts_Book): те же разделы с номерными префиксами, те же
YAML-шапки с `aliases` и `tags`, те же вики-ссылки между заметками. Разница
в содержимом, а не в устройстве: у Cummins ядро хранилища — тексты
документов QuickServe, у LiuGong документов нет, и ядро — паспорта деталей,
составы узлов и парк.

    00 Главная.md              с чего начать, счётчики, ссылки на индексы
    Как искать в этой базе.md  поиск по номеру, по названию, по машине
    01 Индексы/                алфавит деталей, цены, замены, узлы, парк
    10 Машины/                 по заметке на каталог машины
    20 Разделы/<машина>/       разделы каталога машины
    30 Детали/<цифра>/         по заметке на номер детали
    40 Узлы/<машина>/          по заметке на узел, с составом
    60 Темы/                   полки: фильтры, уплотнения, крепёж…
    90 Приложения/             чего в выгрузке нет и почему

Картинки в заметки не вкладываются. Фотографии и чертежи лежат рядом с
каталогом (`media/`), а Obsidian показывает только то, что внутри
хранилища; копировать сюда триста мегабайт ради второго экземпляра тех же
файлов незачем. Вместо этого в заметке стоит ссылка на карточку в
веб-версии базы — она открывает и фотографии, и чертёж.
"""
import json
import os
import re
import shutil
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lgraw                                       # noqa: E402
from lgraw import ROOT, norm                       # noqa: E402

VAULT = os.path.join(ROOT, "obsidian-vault")


def read_global(path, name):
    if not os.path.exists(path):
        return None
    src = open(path, encoding="utf-8").read()
    m = re.search(r"window\.%s\s*=\s*(.*);\s*$" % name, src, re.S)
    return json.loads(m.group(1)) if m else None


def read_data(path, key):
    if not os.path.exists(path):
        return None
    src = open(path, encoding="utf-8").read()
    m = re.search(r'window\.__DATA__\["%s"\]=(.*);\s*$' % re.escape(key), src, re.S)
    return json.loads(m.group(1)) if m else None


def safe(name):
    """Имя файла, которое переживёт Windows, macOS и синхронизацию."""
    s = re.sub(r'[\\/:*?"<>|#\[\]^]', "-", str(name or ""))
    s = re.sub(r"\s+", " ", s).strip(" .")
    return s[:120] or "без-имени"


def slug(s):
    s = re.sub(r"\s+", "-", str(s or "").strip().lower())
    return re.sub(r"[^0-9a-zA-Zа-яё-]", "", s)


def yaml_list(items):
    return "".join('\n  - "%s"' % str(i).replace('"', "'") for i in items)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def part_note_name(no):
    return safe(no)


def part_link(no, parts, label=None):
    if no not in parts:
        return "`%s`" % no
    return "[[%s%s]]" % (part_note_name(no), "|" + label if label else "")


def main():
    parts = read_global(os.path.join(ROOT, "data", "kb_parts.js"), "KB_PARTS")
    topics = read_global(os.path.join(ROOT, "data", "kb_topics.js"), "KB_TOPICS") or []
    machines = read_global(os.path.join(ROOT, "data", "kb_machines.js"), "KB_MACHINES") or {}
    meta = read_global(os.path.join(ROOT, "data", "kb_meta.js"), "KB_META") or {}
    books = read_global(os.path.join(ROOT, "books.js"), "BOOKS") or []
    fleet = read_global(os.path.join(ROOT, "fleet.js"), "FLEET") or []
    if not parts:
        raise SystemExit("нет data/kb_parts.js — сначала tools/build_kb.py")
    by_code = {b["code"]: b for b in books}

    info = {}
    kb_dir = os.path.join(ROOT, "data", "kb")
    for fn in sorted(os.listdir(kb_dir)):
        m = re.match(r"p-(.+)\.js$", fn)
        if m:
            info.update(read_data(os.path.join(kb_dir, fn), "p:" + m.group(1)) or {})
    supply = {}
    sup_dir = os.path.join(ROOT, "data", "supply")
    if os.path.isdir(sup_dir):
        for fn in sorted(os.listdir(sup_dir)):
            m = re.match(r"s-(.+)\.js$", fn)
            if m:
                supply.update(read_data(os.path.join(sup_dir, fn), "sup:" + m.group(1)) or {})

    if os.path.isdir(VAULT):
        shutil.rmtree(VAULT)
    os.makedirs(VAULT)

    # --- узлы и применяемость ---------------------------------------------
    uses = defaultdict(list)          # номер -> [(книга, узел, поз., кол-во)]
    unit_notes = {}                   # (книга, узел) -> имя заметки
    units_by_book = defaultdict(list)
    n_units = 0
    for b in books:
        code = b["code"]
        tree = read_data(os.path.join(ROOT, "data", code, "tree.js"), "tree:" + code) or []
        sections = {}

        def walk(nodes, sec):
            for n in nodes:
                if n.get("g"):
                    sections.setdefault(sec, []).append(n)
                walk(n.get("kids") or [], sec)
        for s in tree:
            walk(s.get("kids") or [], s.get("title") or s.get("id"))

        for sec, nodes in sections.items():
            for n in nodes:
                uid = n["id"]
                page = read_data(os.path.join(ROOT, "data", code, "u", uid + ".js"),
                                 "u:%s/%s" % (code, uid))
                if not page:
                    continue
                n_units += 1
                name = safe("%s %s — %s" % (b["model"], uid, n.get("title") or uid))
                unit_notes[(code, uid)] = name
                units_by_book[code].append((sec, name, n, page))
                for r in page.get("rows") or []:
                    if len(r) > 1 and r[1]:
                        uses[r[1]].append((code, uid, r[0], r[3] if len(r) > 3 else ""))

    # --- заметки узлов -----------------------------------------------------
    for code, items in units_by_book.items():
        b = by_code.get(code, {})
        for sec, name, node, page in items:
            rows = page.get("rows") or []
            body = ["---",
                    'type: "Узел"',
                    'unit: "%s"' % page["id"],
                    'machine: "%s"' % b.get("model", code),
                    'assembly: "%s"' % (page.get("r") or ""),
                    'parts_count: %d' % len(rows),
                    "tags:" + yaml_list(["узел", "машина/" + slug(b.get("model", code)),
                                         "раздел/" + slug(sec)]),
                    "---", "",
                    "# %s" % (node.get("title") or page["id"]),
                    "*%s · раздел «%s»*" % (b.get("model", code), sec), "",
                    "> [!abstract] Узел каталога",
                    "> **Машина:** [[%s]]" % safe(b.get("model", code)),
                    "> **Узел:** `%s`" % page["id"],
                    ]
            if page.get("r"):
                body.append("> **Номер сборки:** `%s`" % page["r"])
            if page.get("d"):
                body.append("> **Редакция чертежа:** %s" % page["d"])
            body += ["> **Чертёж и выноски:** [открыть в каталоге](../../../kb.html#/unit/%s/%s)"
                     % (code, page["id"]), "",
                     "## Состав", "",
                     "| Поз. | Номер | Наименование | Кол-во | Примечание |",
                     "|---|---|---|---|---|"]
            for r in rows:
                no = r[1] if len(r) > 1 else ""
                nm = ""
                if no and no in parts:
                    nm = parts[no][0] or parts[no][1] or ""
                elif len(r) > 2:
                    nm = r[2]
                body.append("| %s | %s | %s | %s | %s |" % (
                    r[0] if r else "", part_link(no, parts) if no else "",
                    (nm or "").replace("|", "\\|"),
                    r[3] if len(r) > 3 else "",
                    (r[4] if len(r) > 4 else "").replace("|", "\\|")))
            write(os.path.join(VAULT, "40 Узлы", safe(b.get("model", code)), name + ".md"),
                  "\n".join(body) + "\n")

    # --- заметки деталей ---------------------------------------------------
    for no in sorted(parts):
        # путь заметки считается сразу: тело длинное, и любая переменная,
        # названная `no` внутри него, увела бы файл под чужое имя
        note_path = os.path.join(VAULT, "30 Детали",
                                 no[0] if no[:1].isdigit() else "буквенные",
                                 part_note_name(no) + ".md")
        p = parts[no]
        d = info.get(no, {})
        s = supply.get(no, {})
        ru, en, zh = p[0], p[1], p[2]
        aliases = [x for x in (ru, en, zh) if x]
        tags = ["деталь"]
        if d.get("maint"):
            tags.append("то")
        if d.get("wear"):
            tags.append("износ")
        if s.get("p"):
            tags.append("есть-цена")
        for i, t in enumerate(topics):
            if no in t["ids"]:
                tags.append("тема/" + slug(t["t"]))
        body = ["---",
                "aliases:" + yaml_list(aliases) if aliases else "aliases: []",
                'type: "Деталь"',
                'part: "%s"' % no,
                'name_ru: "%s"' % (ru or "").replace('"', "'"),
                'name_en: "%s"' % (en or "").replace('"', "'"),
                'name_zh: "%s"' % (zh or "").replace('"', "'"),
                "tags:" + yaml_list(tags),
                "---", "",
                "# %s — %s" % (no, ru or en or zh or "без наименования")]
        if en and en != (ru or ""):
            body.append("*%s*" % en)
        if zh:
            body.append("*%s*" % zh)
        body += ["", "> [!abstract] Паспорт детали"]
        for label, key in (("Обозначение", "spec"), ("Масса, кг", "kg"),
                           ("Габариты, мм", "mm"), ("Минимальная партия", "mpq"),
                           ("Группа скидки", "dg"), ("Рекомендация по запасу", "stock"),
                           ("Единица", "unit"), ("Примечание завода", "note")):
            if d.get(key):
                body.append("> **%s:** %s" % (label, d[key]))
        flags = []
        if d.get("maint"):
            flags.append("деталь ТО")
        if d.get("wear"):
            flags.append("быстроизнашивающаяся")
        if d.get("special"):
            flags.append("особый заказ")
        if flags:
            body.append("> **Отметки EPC:** " + ", ".join(flags))
        if d.get("ph"):
            body.append("> **Фотографий:** %d — [открыть карточку](../../kb.html#/part/%s)"
                        % (len(d["ph"]), no))
        if s.get("p"):
            pr = s["p"]
            body += ["", "## Цена по прайс-листу", "",
                     "| Базис | рублей без НДС |", "|---|---|"]
            if pr.get("b1") is not None:
                body.append("| Магадан, Алдан, Хабаровск | %s |" % pr["b1"])
            if pr.get("b2") is not None:
                body.append("| Лесосибирск, Таксимо, Новосибирск | %s |" % pr["b2"])
        if s.get("c") or s.get("f"):
            body += ["", "## Замены и состояние номера", ""]
            for code in s.get("f", []):
                body.append("- **%s**" % code)
            for l in s.get("c", []):
                # именно `tgt`, а не `no`: `no` — номер самой детали, под
                # ним заметка и сохраняется несколькими строками ниже
                tgt = l.get("d") or l["n"]
                body.append("- %s — %s%s" % (
                    ("`%s`" % tgt) if l.get("x") else part_link(tgt, parts),
                    l.get("code", ""),
                    " (в каталоге этого номера нет)" if l.get("x") else ""))
            if s.get("note"):
                body.append("")
                body.append("> Как это записано в EPC: «%s»" % s["note"])
        hits = uses.get(no, [])
        body += ["", "## Где применяется", ""]
        if not hits:
            body.append("В составах узлов не встречается — номер пришёл из паспорта "
                        "или из цепочки замен.")
        else:
            body += ["| Машина | Узел | Поз. | Кол-во |", "|---|---|---|---|"]
            for code, uid, pos, qty in hits[:200]:
                b = by_code.get(code, {})
                note = unit_notes.get((code, uid))
                body.append("| [[%s]] | %s | %s | %s |" % (
                    safe(b.get("model", code)),
                    "[[%s]]" % note if note else "`%s`" % uid, pos, qty))
            if len(hits) > 200:
                body.append("")
                body.append("Показаны первые 200 из %d." % len(hits))
        write(note_path, "\n".join(body) + "\n")

    # --- машины ------------------------------------------------------------
    for code, m in machines.items():
        b = by_code.get(code, {})
        fl = [f for f in fleet if code in (f.get("books") or [])]
        body = ["---",
                'type: "Машина"',
                'model: "%s"' % m["model"],
                'material_no: "%s"' % code,
                'vin: "%s"' % (m.get("vin") or ""),
                "tags:" + yaml_list(["машина", "машина/" + slug(m["model"])]),
                "---", "",
                "# %s" % m["model"],
                "*%s*" % (m.get("kind") or ""), "",
                "> [!abstract] Каталог машины",
                "> **Исполнение (materialNo):** `%s`" % code,
                "> **VIN, по которому выкачан каталог:** `%s`" % (m.get("vin") or "—"),
                "> **Узлов:** %s · **позиций:** %s · **номеров:** %s"
                % (b.get("units", "?"), b.get("lines", "?"), b.get("numbers", "?")),
                "> **Открыть:** [каталог](../kb.html#/machine/%s)" % code, ""]
        if m.get("spec"):
            body += ["> [!note]- Исполнение как его пишет завод", "> " + m["spec"], ""]
        body += ["## Разделы каталога", ""]
        for ch in m.get("ch", []):
            body.append("- **%s** — %s%s (узлов %s)" % (
                ch.get("code", ""), ch.get("en", ""),
                " · " + ch["zh"] if ch.get("zh") else "", ch.get("n", "")))
        body += ["", "## Машины парка на этом каталоге", ""]
        if not fl:
            body.append("В выгрузке парка машин этой модели нет.")
        else:
            body += ["| Предприятие | Машина | VIN | Гар. № | Год | Привязка |",
                     "|---|---|---|---|---|---|"]
            for f in fl:
                fit = {"vin": "каталог по этому VIN",
                       "model": "каталог той же модели"}.get(f.get("fit"), "каталога нет")
                body.append("| %s | %s | `%s` | %s | %s | %s |" % (
                    f.get("be", ""), f.get("name", ""), f.get("sn") or "—",
                    f.get("garage", ""), f.get("year", ""), fit))
        body += ["", "## Узлы", ""]
        secs = defaultdict(list)
        for sec, name, _n, _p in units_by_book.get(code, []):
            secs[sec].append(name)
        for sec in sorted(secs):
            body.append("### %s" % sec)
            body.append("")
            for name in sorted(secs[sec])[:400]:
                body.append("- [[%s]]" % name)
            if len(secs[sec]) > 400:
                body.append("- …ещё %d" % (len(secs[sec]) - 400))
            body.append("")
        write(os.path.join(VAULT, "10 Машины", safe(m["model"]) + ".md"),
              "\n".join(body) + "\n")

    # --- темы --------------------------------------------------------------
    for t in topics:
        body = ["---", 'type: "Тема"',
                "tags:" + yaml_list(["тема", "тема/" + slug(t["t"])]), "---", "",
                "# %s" % t["t"], "", "*%s*" % t["d"], "",
                "Деталей: **%d**." % len(t["ids"]), "",
                "| Номер | Наименование |", "|---|---|"]
        for no in t["ids"][:1500]:
            p = parts.get(no, ["", "", ""])
            body.append("| %s | %s |" % (part_link(no, parts),
                                         (p[0] or p[1] or "").replace("|", "\\|")))
        if len(t["ids"]) > 1500:
            body.append("")
            body.append("Показаны первые 1500 из %d." % len(t["ids"]))
        write(os.path.join(VAULT, "60 Темы", safe(t["t"]) + ".md"), "\n".join(body) + "\n")

    # --- индексы -----------------------------------------------------------
    idx = os.path.join(VAULT, "01 Индексы")
    letters = defaultdict(list)
    for no in sorted(parts):
        letters[no[0].upper()].append(no)
    body = ["---", 'type: "Индекс"', "tags:\n  - \"индекс\"", "---", "",
            "# Детали — алфавитный указатель", "",
            "Всего номеров: **%d**." % len(parts), ""]
    for k in sorted(letters):
        body.append("## %s — %d" % (k, len(letters[k])))
        body.append("")
        body.append(", ".join(part_link(n, parts) for n in letters[k][:500]))
        if len(letters[k]) > 500:
            body.append("")
            body.append("…ещё %d." % (len(letters[k]) - 500))
        body.append("")
    write(os.path.join(idx, "Детали — алфавитный указатель.md"), "\n".join(body) + "\n")

    priced = [n for n in sorted(parts) if (supply.get(n) or {}).get("p")]
    body = ["---", 'type: "Индекс"', "tags:\n  - \"индекс\"", "---", "",
            "# Детали с ценой", "",
            "Номеров каталога, найденных в «Прайс-листе Люгонг»: **%d**." % len(priced), "",
            "| Номер | Наименование | Базис 1, ₽ | Базис 2, ₽ |", "|---|---|---|---|"]
    for n in priced[:4000]:
        p = supply[n]["p"]
        nm = parts[n][0] or parts[n][1] or ""
        body.append("| %s | %s | %s | %s |" % (part_link(n, parts), nm.replace("|", "\\|"),
                                               p.get("b1", ""), p.get("b2", "")))
    if len(priced) > 4000:
        body.append("")
        body.append("Показаны первые 4000 из %d." % len(priced))
    write(os.path.join(idx, "Детали с ценами.md"), "\n".join(body) + "\n")

    chained = [n for n in sorted(parts) if (supply.get(n) or {}).get("c")]
    body = ["---", 'type: "Индекс"', "tags:\n  - \"индекс\"", "---", "",
            "# Цепочки замен", "",
            "Номеров с пометкой о замене: **%d**. Пометка приходит из EPC словами, "
            "в примечании к позиции, и разбирается на сборке." % len(chained), "",
            "| Номер | Замена | Как записано |", "|---|---|---|"]
    for n in chained[:4000]:
        s = supply[n]
        body.append("| %s | %s | %s |" % (
            part_link(n, parts),
            ", ".join(("`%s`" % (l.get("d") or l["n"])) if l.get("x")
                      else part_link(l.get("d") or l["n"], parts) for l in s["c"]),
            (s.get("note") or "").replace("|", "\\|")))
    write(os.path.join(idx, "Цепочки замен.md"), "\n".join(body) + "\n")

    body = ["---", 'type: "Индекс"', "tags:\n  - \"индекс\"", "---", "",
            "# Парк машин", "",
            "Машин LiuGong в парке АО «Полюс»: **%d**." % len(fleet), "",
            "| Предприятие | Парк | Машина | VIN | Гар. № | Год | Каталог |",
            "|---|---|---|---|---|---|---|"]
    for f in sorted(fleet, key=lambda x: (x.get("be", ""), x.get("model", ""), x.get("garage", ""))):
        code = (f.get("books") or [""])[0]
        m = machines.get(code)
        body.append("| %s | %s | %s | `%s` | %s | %s | %s |" % (
            f.get("be", ""), f.get("mvz", ""), f.get("name", ""), f.get("sn") or "—",
            f.get("garage", ""), f.get("year", ""),
            "[[%s]]" % safe(m["model"]) if m else "нет"))
    write(os.path.join(idx, "Парк машин.md"), "\n".join(body) + "\n")

    body = ["---", 'type: "Индекс"', "tags:\n  - \"индекс\"", "---", "",
            "# Узлы машин", "", "Узлов во всех каталогах: **%d**." % n_units, ""]
    for code in sorted(units_by_book):
        m = machines.get(code, {})
        body.append("## %s — %d" % (m.get("model", code), len(units_by_book[code])))
        body.append("")
        body.append("Смотрите [[%s]] — там узлы разложены по разделам каталога."
                    % safe(m.get("model", code)))
        body.append("")
    write(os.path.join(idx, "Узлы машин.md"), "\n".join(body) + "\n")

    write(os.path.join(idx, "Карта хранилища.md"), """---
type: "Индекс"
tags:
  - "индекс"
---

# Карта хранилища

| Папка | Что внутри |
|---|---|
| `01 Индексы` | сквозные указатели: алфавит деталей, цены, замены, узлы, парк |
| `10 Машины` | по заметке на каталог машины: разделы, парк, узлы |
| `30 Детали` | по заметке на номер детали; разложены по первому знаку номера |
| `40 Узлы` | по заметке на узел, с составом и ссылками на детали |
| `60 Темы` | полки: фильтры, уплотнения, крепёж, гидравлика, электрика… |
| `90 Приложения` | чего в выгрузке нет и почему |

Картинок в заметках нет: фотографии и чертежи лежат рядом с каталогом,
в `media/`, а Obsidian показывает только то, что внутри хранилища.
В каждой заметке есть ссылка на карточку в веб-версии базы — она
открывает и фотографии, и чертёж узла.
""")

    write(os.path.join(VAULT, "90 Приложения", "Чего в выгрузке нет.md"), """---
type: "Приложение"
tags:
  - "приложение"
---

# Чего в выгрузке нет и почему

## Документов по ремонту нет

В базе знаний Cummins, сделанной по той же схеме, главный раздел —
документы: три тысячи процедур ремонта, TSB, сервисных бюллетеней и
руководств с полными текстами. Здесь такого раздела нет.

Причина не в сборке, а в источнике. Портал Cummins QuickServe отдаёт
документацию по серийному номеру двигателя. Портал LiuGong EPC
(`epc.liugong.com:800`) отдаёт каталог: дерево разделов, чертежи, составы
узлов, паспорта деталей и фотографии. Документов он не отдаёт вовсе.

Заводить пустой раздел ради сходства с Cummins незачем: он обещал бы то,
чего в выгрузке нет.

## Складских данных нет

У каталога Komatsu АО «Полюс» есть колонки ЕКМТР, остатков, открытой
закупки и аналогов КСУ: для номеров Komatsu эти корпоративные выгрузки
есть. Для номеров LiuGong их не собрано, поэтому в каталоге и в базе
только то, что есть: цена по прайс-листу поставщика на два базиса.

## Каталог сделан на исполнение, а не на модель

У Komatsu книга ЗИП сделана на диапазон заводских номеров: `S/N 30158-UP`.
У LiuGong каталог сделан на исполнение машины (`materialNo`) и в EPC
открывается по VIN конкретного борта.

Поэтому у машины парка две разные привязки, и путать их нельзя:

* **каталог по этому VIN** — состав точный;
* **каталог той же модели** — выкачан по VIN другой машины; исполнения
  совпадают не всегда, состав может отличаться.

В парке это видно отдельной пометкой.
""")

    write(os.path.join(VAULT, "Как искать в этой базе.md"), """---
type: "Справка"
---

# Как искать в этой базе

## По номеру детали

`Ctrl+O` → номер, например `12B0428`. Заметка детали названа номером, так
что находится сразу.

**Кириллические двойники.** В прайс-листе номера набраны вперемешку:
`44С2104` (кириллическая «С») и `44C2104` (латинская «C») выглядят
одинаково, но это разные строки. Сборщик приводит их к одному виду, а
поиск Obsidian — нет. Если по номеру ничего не нашлось, попробуйте
набрать его латиницей.

## По названию

`Ctrl+O` → «фильтр», «уплотнение», «коронка». Русское, английское и
китайское наименования лежат в `aliases`, поэтому поиск по любому из них
приводит к той же заметке.

Русское наименование есть не у всего: там, где деталь нашлась в
прайс-листе с русской подписью, взято оттуда; остальное переведено по
словарю техники; чего перевести не удалось, осталось по-английски.
Показать исходное честнее, чем угадать.

## По машине

`10 Машины` → модель. В заметке машины: разделы каталога, узлы по
разделам и машины парка, которые на этот каталог опираются.

## По теме

`60 Темы` → «Фильтры и элементы», «Уплотнения», «Крепёж», «Детали
технического обслуживания». Это полки, а не классификация: деталь
попадает на полку по своему наименованию.

## По тегам

- `#деталь`, `#узел`, `#машина`, `#тема`, `#индекс`
- `#то` — деталь технического обслуживания по отметке EPC
- `#износ` — быстроизнашивающаяся
- `#есть-цена` — есть в прайс-листе
- `#машина/9125f`, `#тема/фильтры-и-элементы`
""")

    counters = [
        ("Деталей", len(parts)),
        ("Паспортов", meta.get("passports", 0)),
        ("Узлов", n_units),
        ("Машин каталога", len(machines)),
        ("Машин парка", len(fleet)),
        ("С фотографиями", meta.get("photos", 0)),
        ("С ценой", len(priced)),
        ("С цепочкой замен", len(chained)),
        ("Тем", len(topics)),
    ]
    home = ["---", 'type: "Главная"', "cssclasses:\n  - \"wide\"", "---", "",
            "# База знаний LiuGong · «Развитие»", "",
            "> [!abstract] Что здесь есть",
            "> " + " · ".join("**%s** %s" % (n, t.lower()) for t, n in counters) + ".",
            "> Всё связано перекрёстными ссылками: деталь → узел → машина → парк.",
            "",
            "## С чего начать", "",
            "| Задача | Куда идти |", "|---|---|",
            "| Найти деталь по номеру | `Ctrl+O` → номер, например `12B0428` |",
            "| Найти деталь по названию | `Ctrl+O` → «фильтр», «коронка» — работает по-русски |",
            "| Понять, куда деталь ставится | заметка детали → «Где применяется» |",
            "| Посмотреть состав узла | `40 Узлы` или заметка машины |",
            "| Понять, чем деталь заменена | [[Цепочки замен]] |",
            "| Узнать цену | [[Детали с ценами]] |",
            "| Собрать список на ТО | [[Детали технического обслуживания]] |",
            "| Найти машину по VIN | [[Парк машин]] |",
            "| Разобраться в поиске | [[Как искать в этой базе]] |",
            "", "## Машины", ""]
    for code, m in machines.items():
        b = by_code.get(code, {})
        n = len([f for f in fleet if code in (f.get("books") or [])])
        home.append("- [[%s]] — %s · узлов %s, позиций %s, в парке %d"
                    % (safe(m["model"]), m.get("kind", ""), b.get("units", "?"),
                       b.get("lines", "?"), n))
    home += ["", "## Индексы", "",
             "- [[Детали — алфавитный указатель]]",
             "- [[Детали с ценами]]",
             "- [[Цепочки замен]]",
             "- [[Узлы машин]]",
             "- [[Парк машин]]",
             "- [[Карта хранилища]]",
             "", "## Темы", ""]
    for t in topics:
        home.append("- [[%s]] — %s (%d)" % (safe(t["t"]), t["d"], len(t["ids"])))
    home += ["", "## Чего здесь нет", "",
             "- [[Чего в выгрузке нет]] — про документы, склад и привязку каталога "
             "к исполнению машины"]
    write(os.path.join(VAULT, "00 Главная.md"), "\n".join(home) + "\n")

    write(os.path.join(VAULT, "README.md"), """# Хранилище Obsidian — база знаний LiuGong

Открывается как хранилище Obsidian: «Открыть папку как хранилище» →
`obsidian-vault`. Начните с `00 Главная`.

Собирается `tools/build_vault.py` из тех же данных, что и веб-версия базы
(`kb.html`). Править заметки руками смысла нет: следующая сборка их
перезапишет. Правки вносятся в сборщик.
""")

    n_notes = sum(len(f) for _r, _d, f in os.walk(VAULT))
    print("хранилище собрано: %d заметок (деталей %d, узлов %d, машин %d, тем %d)"
          % (n_notes, len(parts), n_units, len(machines), len(topics)))


if __name__ == "__main__":
    main()
