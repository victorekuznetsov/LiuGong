"""База знаний LiuGong — сборка данных.

    python3 tools/build_kb.py                 всё
    python3 tools/build_kb.py --no-photos     без пережатия фотографий

Сделана по образцу базы знаний Cummins (`kb.js` и `data/kb_*.js` в
Cummins_Parts_Book): те же разделы, те же имена файлов, тот же вид
карточек и та же идея — всё связано сквозными ссылками, деталь → узел →
машина → парк, а тела грузятся кусками по мере надобности, поэтому база
работает и без сервера.

Отличие от базы Cummins — в том, что есть на входе, а не в том, как она
устроена. У Cummins основа базы — документы QuickServe: три тысячи
процедур, TSB и бюллетеней с полными текстами. У LiuGong в EPC документов
нет вовсе: портал отдаёт каталог, паспорта деталей и фотографии. Поэтому
здесь вместо раздела документов — паспорта деталей и темы, собранные по
самим деталям, и об отсутствии документов сказано прямо, а не спрятано за
пустым разделом.

На выходе:

    data/kb_parts.js      краткая опись всех номеров (для списка и поиска)
    data/kb/p-<XX>.js     паспорта деталей шардами (их же читает каталог)
    data/kb_machines.js   машины каталога: разделы, счётчики, привязка
    data/kb_topics.js     темы: детали, собранные по назначению
    data/kb_search.js     поисковый индекс
    data/kb_photos.js     у каких номеров есть фотографии
    data/kb_meta.js       счётчики для стартовой страницы
    media/photos/<номер>/NN.jpg   фотографии, пережатые под экран
"""
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lgraw                                       # noqa: E402
import build_catalog                               # noqa: E402
from lgraw import ROOT, norm                       # noqa: E402

PHOTO_MAX = 900
PHOTO_Q = 80

# Темы: деталь попадает в тему, если её английское наименование содержит
# одно из слов. Список составлен по частотнику наименований каталога —
# это не попытка классифицировать всё, а несколько полок, с которых чаще
# всего снимают.
TOPICS = [
    ("Фильтры и элементы", "Фильтры всех систем и сменные элементы",
     ["FILTER", "ELEMENT", "CARTRIDGE", "STRAINER", "SEPARATOR", "BREATHER"]),
    ("Уплотнения", "Кольца, сальники, прокладки, манжеты",
     ["O-RING", "ORING", "SEAL", "GASKET", "PACKING", "RING", "DUST PROOF"]),
    ("Крепёж", "Болты, гайки, шайбы, шплинты, штифты",
     ["BOLT", "NUT", "WASHER", "SCREW", "PIN", "COTTER", "RIVET", "STUD", "CLAMP"]),
    ("Гидравлика", "Насосы, клапаны, цилиндры, шланги, трубки",
     ["PUMP", "VALVE", "CYLINDER", "HOSE", "TUBE", "PIPE", "FITTING", "ACCUMULATOR",
      "MANIFOLD", "SWIVEL", "MOTOR"]),
    ("Двигатель", "Блок, головка, поршневая, топливная аппаратура",
     ["ENGINE", "PISTON", "CRANK", "CAMSHAFT", "CYLINDER HEAD", "INJECTOR",
      "TURBO", "NOZZLE", "ROCKER", "LINER", "BEARING SHELL"]),
    ("Охлаждение", "Радиаторы, вентиляторы, термостаты, патрубки",
     ["RADIATOR", "COOLER", "FAN", "THERMOSTAT", "WATER PUMP", "CONDENSER",
      "INTERCOOLER", "EXPANSION TANK"]),
    ("Электрика", "Жгуты, реле, датчики, освещение, приборы",
     ["HARNESS", "WIRE", "CABLE", "RELAY", "FUSE", "SENSOR", "SWITCH", "LAMP",
      "LIGHT", "BATTERY", "ALTERNATOR", "STARTER", "CONTROLLER", "DISPLAY",
      "CAMERA", "BEACON", "HORN"]),
    ("Ходовая часть", "Гусеницы, катки, колёса, мосты, тормоза",
     ["TRACK", "ROLLER", "IDLER", "SPROCKET", "SHOE", "CHAIN", "TIRE", "RIM",
      "AXLE", "HUB", "BRAKE", "DISC", "DRUM"]),
    ("Рабочее оборудование", "Стрела, рукоять, ковш, зубья, коронки",
     ["BOOM", "ARM", "BUCKET", "TOOTH", "TEETH", "CROWN", "ADAPTER", "LIP",
      "CUTTING EDGE", "BLADE"]),
    ("Кабина и оперение", "Кабина, стёкла, сиденье, капоты, ограждения",
     ["CAB", "GLASS", "WIPER", "SEAT", "DOOR", "MIRROR", "HOOD", "COVER",
      "GUARD", "PANEL", "HANDRAIL", "LADDER", "AIR CONDITION"]),
    ("Смазка", "Централизованная смазка, шприцы, маслёнки",
     ["GREASE", "LUBRICAT", "NIPPLE", "OILER"]),
]

FLAG_TOPICS = [
    ("Детали технического обслуживания", "Отмечены в EPC как детали ТО", "maint"),
    ("Быстроизнашивающиеся", "Отмечены в EPC как быстроизнашивающиеся", "wear"),
    ("Ремкомплекты", "Позиции, которые EPC отдаёт комплектом", "kit"),
    ("Снятые с производства", "Завод прекратил поставку; смотрите цепочку замен", "off"),
    ("С ценой в прайс-листе", "Есть в «Прайс-листе Люгонг»", "priced"),
]


def attrs_of(info, locale):
    loc = ((info or {}).get("locales") or {}).get(locale) or {}
    return loc.get("attrs") or {}, loc.get("attrsRaw") or {}


def yes(v):
    return str(v or "").strip().lower() in ("да", "yes", "y", "true", "1", "是")


def clean(v):
    v = re.sub(r"\s+", " ", str(v or "")).strip()
    return "" if v in ("", "0.0", "0.0*0.0*0.0", "-") else v


def size_mm(v):
    v = clean(v).replace("*", " × ")
    return re.sub(r"\s+", " ", v).strip(" ×")


def collect(no_photos=False):
    books = lgraw.books()

    parts = {}          # номер как в каталоге -> паспорт
    uses = Counter()    # сколько раз номер встречается в составах
    in_books = defaultdict(set)
    names_en = {}
    names_zh = {}
    photo_src = {}      # номер -> [(книга, файл), …]

    for code in books:
        for legend in lgraw.legends(code):
            en = lgraw.parts(code, legend, "en_US")
            zh = lgraw.parts(code, legend, "zh_CN")
            zh_by = {}
            for r in zh:
                zh_by[(str(r.get("callout")), r.get("partNO"))] = (r.get("partName") or "").strip()
            for r in en:
                p = (r.get("partNO") or "").strip()
                if not p:
                    continue
                uses[p] += 1
                in_books[p].add(code)
                n = (r.get("partName") or "").strip()
                if n:
                    names_en.setdefault(p, n)
                z = zh_by.get((str(r.get("callout")), p), "")
                if z:
                    names_zh.setdefault(p, z)

    for code in books:
        d = lgraw.raw(code, "partinfo")
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if not fn.endswith(".json"):
                continue
            p = fn[:-5]
            if p in parts:
                continue
            info = lgraw.jload(os.path.join(d, fn))
            if not info:
                continue
            zh_a, zh_raw = attrs_of(info, "zh_CN")
            en_a, en_raw = attrs_of(info, "en_US")
            rec = {
                "en": clean(en_a.get("partName") or names_en.get(p, "")),
                "zh": clean(zh_a.get("partName") or names_zh.get(p, "")),
                "spec": clean(en_a.get("spec") or zh_a.get("spec")),
                "kg": clean(zh_a.get("weightKg") or en_raw.get("Weight")),
                "mm": size_mm(zh_a.get("sizeMm") or en_raw.get("Size")),
                "mpq": clean(zh_a.get("mpq") or en_raw.get("Minimum packaging unit")),
                "dg": clean(zh_a.get("discountGroup") or en_raw.get("Transaction discount group")),
                "stock": clean(en_raw.get("Inventory Sug") or zh_a.get("stockAdvice")),
                "unit": clean(zh_a.get("unit") or en_a.get("unit")),
                "note": clean(zh_a.get("note") or en_raw.get("Remark")),
                "maint": 1 if yes(zh_a.get("isMaintenance")) else 0,
                "wear": 1 if yes(zh_a.get("isWear")) else 0,
                "special": 1 if yes(zh_a.get("isSpecialPurchase")) else 0,
                "up": clean(info.get("parentPartNO")),
            }
            parts[p] = {k: v for k, v in rec.items() if v not in ("", 0)}
        pd = lgraw.raw(code, "photos")
        if os.path.isdir(pd):
            for p in os.listdir(pd):
                if p in photo_src:
                    continue
                files = lgraw.photos(code, p)
                if files:
                    photo_src[p] = [(code, f) for f in files]

    # номера, у которых паспорта нет, но в составах они есть
    for p in uses:
        if p not in parts:
            rec = {}
            if names_en.get(p):
                rec["en"] = names_en[p]
            if names_zh.get(p):
                rec["zh"] = names_zh[p]
            parts[p] = rec
        else:
            if not parts[p].get("en") and names_en.get(p):
                parts[p]["en"] = names_en[p]
            if not parts[p].get("zh") and names_zh.get(p):
                parts[p]["zh"] = names_zh[p]

    photos = {}
    if not no_photos:
        photos = shrink_photos(photo_src)
    else:
        photos = {p: ["media/photos/%s/%s" % (p, f) for _c, f in v]
                  for p, v in photo_src.items()}
    return parts, uses, in_books, photos


def shrink_photos(photo_src):
    """Пережать фотографии деталей под экран.

    Из EPC они приходят как есть со склада — по 1600×1200 и 400 КБ штука,
    шесть с половиной тысяч файлов, два с половиной гигабайта. В карточке
    детали такая фотография показывается в двести пикселей шириной, а во
    весь экран — не больше девятисот. Всё, что сверху, — это только вес
    репозитория и время загрузки.
    """
    from PIL import Image
    out_root = os.path.join(ROOT, "media", "photos")
    os.makedirs(out_root, exist_ok=True)
    out = {}
    done = 0
    for part, files in sorted(photo_src.items()):
        safe = re.sub(r"[^0-9A-Za-z_.-]", "_", part)
        dst_dir = os.path.join(out_root, safe)
        rel = []
        for code, fn in files:
            src = lgraw.raw(code, "photos", part, fn)
            name = os.path.splitext(fn)[0] + ".jpg"
            dst = os.path.join(dst_dir, name)
            relpath = "media/photos/%s/%s" % (safe, name)
            if not os.path.exists(dst):
                os.makedirs(dst_dir, exist_ok=True)
                try:
                    im = Image.open(src)
                    im.load()
                    if max(im.size) > PHOTO_MAX:
                        k = PHOTO_MAX / max(im.size)
                        im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))),
                                       Image.LANCZOS)
                    im.convert("RGB").save(dst, "JPEG", quality=PHOTO_Q,
                                           optimize=True, progressive=True)
                except Exception as e:
                    print("  фото %s/%s: %s" % (part, fn, e))
                    continue
            rel.append(relpath)
            done += 1
        if rel:
            out[part] = rel
    print("фотографий пережато/на месте: %d у %d номеров" % (done, len(out)))
    return out


def topic_of(name):
    up = (name or "").upper()
    hits = []
    for i, (_t, _d, words) in enumerate(TOPICS):
        if any(w in up for w in words):
            hits.append(i)
    return hits


def main(argv):
    no_photos = "--no-photos" in argv
    parts, uses, in_books, photos = collect(no_photos)

    ru = {}
    ru_path = os.path.join(ROOT, "data", "ru.js")
    if os.path.exists(ru_path):
        m = re.search(r'window\.__DATA__\["ru"\]=(\{.*\});', open(ru_path, encoding="utf-8").read(), re.S)
        if m:
            ru = json.loads(m.group(1))

    supply = {}
    sup_dir = os.path.join(ROOT, "data", "supply")
    if os.path.isdir(sup_dir):
        for fn in sorted(os.listdir(sup_dir)):
            if not fn.endswith(".js"):
                continue
            m = re.search(r'window\.__DATA__\["sup:[^"]+"\]=(\{.*\});',
                          open(os.path.join(sup_dir, fn), encoding="utf-8").read(), re.S)
            if m:
                supply.update(json.loads(m.group(1)))

    # --- паспорта шардами -------------------------------------------------
    shards = defaultdict(dict)
    for p, rec in parts.items():
        rec = dict(rec)
        if rec.get("en") and ru.get(rec["en"]):
            rec["ru"] = ru[rec["en"]]
        if photos.get(p):
            rec["ph"] = photos[p]
        rec["u"] = uses.get(p, 0)
        rec["b"] = sorted(in_books.get(p, ()))
        shards[norm(p)[:2] or "__"][p] = rec
    kb_dir = os.path.join(ROOT, "data", "kb")
    if os.path.isdir(kb_dir):
        shutil.rmtree(kb_dir)
    os.makedirs(kb_dir)
    for name, obj in shards.items():
        lgraw.write_data(os.path.join(kb_dir, "p-%s.js" % name), "p:" + name, obj)

    # --- краткая опись и поиск --------------------------------------------
    index, search = {}, []
    for p in sorted(parts):
        rec = parts[p]
        en = rec.get("en", "")
        rus = ru.get(en, "")
        s = supply.get(p) or {}
        f = 0
        if rec.get("maint"):
            f |= 1
        if rec.get("wear"):
            f |= 2
        if rec.get("special"):
            f |= 4
        if photos.get(p):
            f |= 8
        if s.get("p"):
            f |= 16
        if "off" in (s.get("f") or []):
            f |= 32
        if s.get("c"):
            f |= 64
        index[p] = [rus, en, rec.get("zh", ""), uses.get(p, 0), f]
        search.append([p, rus, en, rec.get("zh", "")])

    lgraw.write_global(os.path.join(ROOT, "data", "kb_parts.js"), "KB_PARTS", index,
                       "Опись деталей базы знаний. Пересобирается tools/build_kb.py.")
    lgraw.write_global(os.path.join(ROOT, "data", "kb_search.js"), "KB_SEARCH", search,
                       "Поисковый индекс базы знаний. tools/build_kb.py.")
    lgraw.write_global(os.path.join(ROOT, "data", "kb_photos.js"), "KB_PHOTOS", photos,
                       "Фотографии деталей. tools/build_kb.py.")

    # --- машины ------------------------------------------------------------
    machines = {}
    for code in lgraw.books():
        m = lgraw.machine(code)
        secs = []
        for sec in lgraw.tree(code, "en_US"):
            n = sum(1 for _ in lgraw.walk(sec.get("children") or []))
            secs.append({"code": sec.get("code") or sec.get("id"),
                         "en": (sec.get("name") or "").strip(), "n": n})
        zh_sec = {}
        for sec in lgraw.tree(code, "zh_CN"):
            zh_sec[sec.get("code") or sec.get("id")] = (sec.get("name") or "").strip()
        for s in secs:
            s["zh"] = zh_sec.get(s["code"], "")
        machines[code] = {
            "model": build_catalog.model_short(m.get("subModel") or code),
            "model_full": (m.get("subModel") or code).strip(),
            "kind": build_catalog.KIND_RU.get((m.get("machineType") or "").strip(),
                                              (m.get("machineType") or "").strip()),
            "kind_zh": (m.get("machineType") or "").strip(),
            "line": build_catalog.LINE_RU.get((m.get("productLine") or "").strip(),
                                              (m.get("productLine") or "").strip()),
            "vin": (m.get("vin") or "").strip(),
            "spec": (m.get("materialNo") or "").strip(),
            "ch": secs,
        }
    lgraw.write_global(os.path.join(ROOT, "data", "kb_machines.js"), "KB_MACHINES", machines,
                       "Машины базы знаний. tools/build_kb.py.")

    # --- темы --------------------------------------------------------------
    buckets = defaultdict(list)
    for p in sorted(parts):
        for i in topic_of(parts[p].get("en", "")):
            buckets[i].append(p)
    topics = []
    for i, (t, d, _w) in enumerate(TOPICS):
        if buckets.get(i):
            topics.append({"t": t, "d": d, "ids": buckets[i]})
    flag_sets = {
        "maint": [p for p in sorted(parts) if parts[p].get("maint")],
        "wear": [p for p in sorted(parts) if parts[p].get("wear")],
        "kit": [p for p in sorted(parts) if "KIT" in (parts[p].get("en", "") or "").upper()],
        "off": [p for p in sorted(parts) if "off" in ((supply.get(p) or {}).get("f") or [])],
        "priced": [p for p in sorted(parts) if (supply.get(p) or {}).get("p")],
    }
    for t, d, key in FLAG_TOPICS:
        if flag_sets.get(key):
            topics.append({"t": t, "d": d, "ids": flag_sets[key]})
    lgraw.write_global(os.path.join(ROOT, "data", "kb_topics.js"), "KB_TOPICS", topics,
                       "Темы базы знаний. tools/build_kb.py.")

    meta = {
        "parts": len(parts),
        "passports": sum(1 for p in parts if parts[p].get("mpq") or parts[p].get("kg")),
        "photos": len(photos),
        "photo_files": sum(len(v) for v in photos.values()),
        "priced": len(flag_sets["priced"]),
        "chains": sum(1 for p in parts if (supply.get(p) or {}).get("c")),
        "machines": len(machines),
        "topics": len(topics),
        "ru": sum(1 for p in parts if ru.get(parts[p].get("en", ""))),
    }
    lgraw.write_global(os.path.join(ROOT, "data", "kb_meta.js"), "KB_META", meta,
                       "Счётчики базы знаний. tools/build_kb.py.")
    print("деталей %d, паспортов %d, с фотографиями %d (%d файлов), "
          "с ценой %d, с заменами %d, тем %d"
          % (meta["parts"], meta["passports"], meta["photos"], meta["photo_files"],
             meta["priced"], meta["chains"], meta["topics"]))


if __name__ == "__main__":
    main(sys.argv)
