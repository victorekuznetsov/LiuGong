"""Русские наименования для каталога LiuGong.

    python3 tools/build_translate.py      (после build_catalog.py)

Пишет `data/ru.js` — таблицу «английское наименование → русское». Китайские
наименования отдельно переводить не нужно: они заводские и собираются
прямо в build_catalog.py (`data/names.js`).

Русское берётся из двух источников, и первый важнее второго.

**Прайс-лист.** В «Прайс-листе Люгонг» часть позиций подписана
по-русски — «Воздушный фильтр», «Коронка», «Палец». Это живое
наименование от поставщика, а не машинный перевод, и оно заведомо лучше
любого словаря. Английское наименование той же детали берётся из каталога,
и так получается пара.

Пара принимается не с первого совпадения. Одно и то же английское
наименование (`PIN`) стоит у сотен разных номеров, и у каждого в прайсе
может быть своя подпись. Поэтому: русское наименование должно сойтись
минимум на двух разных номерах деталей и собрать больше половины голосов.
Одного номера мало — у ходовой детали подпись поставщика может относиться
к конкретному применению, и `PIN` молча стал бы «пальцем ковша».

**Словарь.** Остальное переводится по `tools/en_ru_dict.py` — словарь
техники взят из каталога Komatsu, предметная область та же, — но не как
попало:

* готовый оборот из `EN_RU_PHRASES` (`FUEL SYSTEM` → «топливная
  система», `FILTER ELEMENT` → «фильтрующий элемент»);
* хвост сборки и группы (`HOSE AS` → «шланг в сборе», `PLATE GP` →
  «пластина, группа», `DOOR-LH` → «дверь, левая»);
* пословно — и только для однословных наименований.

Пословный перевод многословного наименования по-русски не собирается:
выходит «топливо система» и «фильтр элемент», потому что там другой
порядок слов и другое согласование, а склеить их по словарю нельзя.
Такое наименование остаётся по-английски.

Это стоит покрытия: со сплошным пословным переводом покрывается 97 %
вхождений, с разбором — 86 %. Но оставшиеся 14 % честно читаются как
`PISTON PUMP`, а не как «поршень насос». Неверный перевод детали хуже
отсутствующего: по нему закажут не то.
"""
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lgraw                                      # noqa: E402
from lgraw import ROOT, norm                      # noqa: E402
from en_ru_dict import EN_RU, EN_RU_PHRASES        # noqa: E402
import build_supply                                # noqa: E402

CYR = re.compile(r"[А-Яа-яЁё]")
WORD = re.compile(r"[A-Za-z][A-Za-z'0-9]*")
# Слова-обозначения: переводить нечего, оставляем как есть.
KEEP = re.compile(r"^(?:[A-Z]|[A-Z]?\d+[A-Z0-9.\-]*|LH|RH|[IVX]+)$")


def is_russian(s):
    letters = re.sub(r"[^A-Za-zА-Яа-яЁё]", "", s or "")
    if not letters:
        return False
    return len(CYR.findall(letters)) * 2 > len(letters)


# «HOSE AS», «PLATE GP» — сборка и группа: у LiuGong это хвост
# наименования, а не отдельное слово в ряду.
TAIL = [(re.compile(r"\s+(?:AS|ASM|ASSY|ASSEMBLY)\.?$", re.I), " в сборе"),
        (re.compile(r"\s+(?:GP|GROUP)\.?$", re.I), ", группа"),
        (re.compile(r"\s*-\s*LH$", re.I), ", левый"),
        (re.compile(r"\s*-\s*RH$", re.I), ", правый")]


def by_dictionary(name):
    """Перевод наименования; None — если перевести целиком не вышло.

    Порядок такой: сначала готовый оборот, потом хвост «в сборе» и
    «группа» с переводом головы, и только потом — пословно, и только для
    однословных наименований. Пословный перевод многословного даёт
    «топливо система» вместо «топливная система»: по-русски там другой
    порядок слов и другое согласование, а склеить их по словарю нельзя.
    Такое наименование лучше оставить по-английски.
    """
    src = re.sub(r"\s+", " ", (name or "")).strip()
    if not src:
        return None
    # В выгрузке попадаются длинное тире и минус вместо дефиса: `O—RING`
    # и `O-RING` — одно и то же наименование.
    key = re.sub(r"[\u2010-\u2015\u2212]", "-", src).upper()
    hit = EN_RU_PHRASES.get(key)
    if hit:
        return hit
    for rx, tail in TAIL:
        if rx.search(src):
            head = by_dictionary(rx.sub("", src))
            if head:
                return head + tail
            return None
    words = WORD.findall(src)
    if len(words) > 1:
        return None
    name = src
    out, unknown = [], 0
    for w in words:
        up = w.upper()
        if KEEP.match(up):
            out.append(w)
            continue
        t = EN_RU.get(up)
        if t is None:
            unknown += 1
            out.append(w)
        else:
            out.append(t)
    if unknown:
        return None
    # Сохранить пунктуацию исходной строки: `SEAL, O-RING` -> `сальник, кольцо`
    i = [0]

    def sub(_m):
        w = out[i[0]]
        i[0] += 1
        return w
    res = WORD.sub(sub, name)
    res = re.sub(r"\s+", " ", res).strip(" ,;")
    return capitalize(res)


def capitalize(s):
    """С заглавной — первую букву, а не первый знак.

    В выгрузке попадаются наименования со случайной кавычкой в начале
    (`"BRACKET`), и `s[0].upper()` в таком случае поднимает кавычку,
    а слово остаётся строчным."""
    if not s:
        return None
    for i, ch in enumerate(s):
        if ch.isalpha():
            return s[:i] + ch.upper() + s[i + 1:]
    return s


def main():
    # английское наименование -> номера деталей, у которых оно стоит
    names = defaultdict(set)
    titles = set()
    for code in lgraw.books():
        for legend in lgraw.legends(code):
            for r in lgraw.parts(code, legend, "en_US"):
                n = (r.get("partName") or "").strip()
                if n:
                    names[n].add(norm(r.get("partNO") or ""))
        for n in lgraw.walk(lgraw.tree(code, "en_US")):
            t = (n.get("name") or "").strip()
            if t:
                titles.add(t)

    prices, _ = build_supply.read_prices()
    ru_price = {}
    for key, (_p1, _p2, pname) in prices.items():
        if pname and is_russian(pname):
            ru_price[key] = re.sub(r"\s+", " ", pname).strip()

    # голосование: английское наименование -> какое русское ему отвечает
    votes = defaultdict(Counter)
    voters = defaultdict(set)
    for en, parts in names.items():
        for p in parts:
            ru = ru_price.get(p)
            if ru:
                votes[en][ru.lower()] += 1
                voters[en].add(p)

    table, from_price, from_dict = {}, 0, 0
    for en in sorted(names):
        v = votes.get(en)
        if v and len(voters[en]) >= 2:
            top, n = v.most_common(1)[0]
            if n * 2 > sum(v.values()):
                table[en] = capitalize(top)
                from_price += 1
                continue
        t = by_dictionary(en)
        if t:
            table[en] = t
            from_dict += 1

    for t in sorted(titles):
        if t in table:
            continue
        d = by_dictionary(t)
        if d:
            table[t] = d
            from_dict += 1

    lgraw.write_data(os.path.join(ROOT, "data", "ru.js"), "ru", table,
                     "Русские наименования. Пересобирается tools/build_translate.py.")
    total = len(names) + len(titles)
    print("наименований %d (позиций %d, заголовков %d); переведено %d — "
          "из прайс-листа %d, по словарю %d; осталось по-английски %d"
          % (total, len(names), len(titles), len(table), from_price, from_dict,
             total - len(table)))


if __name__ == "__main__":
    main()
