"""Чтение выгрузки EPC LiuGong. Общее для всех сборщиков.

Выгрузка лежит в ветке `EPC_rawdata` этого же репозитория: по каталогу на
машину, внутри — дерево разделов на двух языках, описи чертежей, состав
каждого чертежа, сами чертежи и паспорта деталей. Путь к ней задаётся
переменной окружения `LG_RAWDATA`; по умолчанию — `rawdata/` рядом с
репозиторием.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAWDATA = os.environ.get("LG_RAWDATA") or os.path.join(ROOT, "rawdata")


def raw(*parts):
    return os.path.join(RAWDATA, *parts)


def jload(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def books():
    """Коды книг (они же modelCode машины) в выгрузке."""
    if not os.path.isdir(RAWDATA):
        raise SystemExit("нет выгрузки EPC: %s\n"
                         "Возьмите её из ветки EPC_rawdata или задайте LG_RAWDATA."
                         % RAWDATA)
    out = []
    for name in sorted(os.listdir(RAWDATA)):
        if os.path.isfile(raw(name, "legends.json")):
            out.append(name)
    return out


def machine(code):
    return jload(raw(code, "machine.json"), {}) or {}


def legends(code):
    return jload(raw(code, "legends.json"), {}) or {}


def tree(code, locale="en_US"):
    d = jload(raw(code, "tree_%s.json" % locale), None)
    if not d:
        return []
    return (d.get("result") or {}).get("data") or []


def parts(code, legend, locale="en_US"):
    return jload(raw(code, "parts", locale, legend + ".json"), []) or []


def partinfo(code, part):
    return jload(raw(code, "partinfo", part + ".json"), None)


def photos(code, part):
    d = raw(code, "photos", part)
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d) if f.lower().endswith((".jpg", ".jpeg", ".png")))


def drawing(code, legend):
    """Чертёж как текст SVG; None — если его не выкачали."""
    import gzip
    p = raw(code, "drawings", legend + ".svgz")
    if not os.path.exists(p):
        return None
    with gzip.open(p, "rt", encoding="utf-8", errors="replace") as f:
        return f.read()


def walk(nodes):
    for n in nodes:
        yield n
        for k in walk(n.get("children") or []):
            yield k


# ---------------------------------------------------------------- мелочи --

# Кириллические двойники латинских букв. В прайс-листе номера набраны
# вперемешку: `44С2104` и `44C2104` выглядят одинаково, но это разные
# строки, и без приведения половина цен к каталогу не привяжется.
LOOKALIKE = str.maketrans("АВЕКМНОРСТУХавекмнорстух",
                          "ABEKMHOPCTYXABEKMHOPCTYX")


def norm(no):
    """Номер детали для поиска и сверки: без дефисов, точек и пробелов."""
    s = str(no or "").upper().translate(LOOKALIKE)
    return re.sub(r"[^0-9A-Z]", "", s)


LEGEND_RE = re.compile(r"^(.*)_(\d+)_(\d+)$")


def legend_parts(code):
    """`60C6073_003_00` -> ('60C6073', 3, 0): номер сборки, редакция, лист."""
    m = LEGEND_RE.match(code or "")
    if not m:
        return (code or "", 0, 0)
    return (m.group(1), int(m.group(2)), int(m.group(3)))


def eff_date(note):
    """`ST:2025-01-02` и `ST:20160219` -> `2025-01-02`. Иначе пусто."""
    s = (note or "").strip()
    m = re.match(r"^ST:\s*(\d{4})-(\d{2})-(\d{2})$", s)
    if m:
        return "%s-%s-%s" % m.groups()
    m = re.match(r"^ST:\s*(\d{4})(\d{2})(\d{2})$", s)
    if m:
        return "%s-%s-%s" % m.groups()
    m = re.match(r"^(\d{4})(\d{2})(\d{2})$", s)
    if m:
        return "%s-%s-%s" % m.groups()
    return ""


def jsdump(obj):
    """Компактный JSON: файлы данных читает браузер, а не человек."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def write_data(path, key, obj, header=None):
    """Кусок данных как `.js`.

    Не `.json`: каталог должен открываться двойным щелчком по `index.html`,
    а `fetch()` местного файла браузер из-под `file://` не пускает. Тег
    `<script>` этому запрету не подчиняется — так же, как books.js.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if header:
            f.write("/* %s */\n" % header)
        f.write('window.__DATA__["%s"]=%s;\n' % (key, jsdump(obj)))
    os.replace(tmp, path)


def write_global(path, name, obj, header):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("/* %s */\n" % header)
        f.write("window.%s = %s;\n" % (name, json.dumps(obj, ensure_ascii=False, indent=1)))
    os.replace(tmp, path)
