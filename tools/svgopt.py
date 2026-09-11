"""Пережатие чертежей LiuGong EPC и снятие координат выносок.

Чертёж приходит из EPC ровно в том виде, в каком его сохранил Illustrator:
одна линия — один элемент `<line>` с шестью атрибутами оформления, и таких
элементов в листе бывает под две тысячи. Читается это как есть, но в
репозиторий и в браузер такой чертёж класть нельзя: в среднем 360 КБ на лист,
5 818 листов — два гигабайта разметки, из которых собственно геометрия
занимает четверть.

Пережатие ничего не выбрасывает из картинки. Оно делает четыре вещи:

* `<line>` и `<polyline>` переводятся в `<path>`, а идущие подряд соседи с
  одинаковым оформлением сливаются в один `d`. Соседи — обязательное условие:
  порядок отрисовки и наследование от родителя сохраняются в точности.
  Залитые фигуры не сливаются никогда: два контура в одном `d` — это уже не
  две фигуры, а одна с дыркой;
* повторяющиеся наборы атрибутов оформления выносятся в классы CSS;
* координаты округляются до десятых, а запись выбирается короткая из
  абсолютной и относительной. Лист шириной 510 единиц приходит с точностью
  до тысячных — это 0,0002 % ширины, на экране такого нет;
* растровые вставки (у части листов внутри чертежа лежит фотография в
  base64) пережимаются под тот размер, в котором они показываются.

Вместе это даёт примерно троекратное сокращение при неотличимой картинке:
сверка «до и после» на случайной выборке даёт медианное расхождение 0,00 %
пикселей, худшее — около 1,9 %, и это сглаживание линий, сдвинувшихся на
доли пикселя.

Отдельно снимаются выноски: номера позиций на чертеже LiuGong нарисованы —
это элементы `<text>`. Их координаты возвращаются наружу, чтобы каталог мог
положить поверх картинки прозрачные кликабельные области. Сам текст остаётся
в чертеже: рисовать номер поверх нарисованного незачем.
"""
import base64
import io
import re

NUM = re.compile(r"-?\d*\.?\d+(?:[eE][-+]?\d+)?")
ATTR = re.compile(r"([\w:.-]+)\s*=\s*(\"[^\"]*\"|'[^']*')")
TOKEN = re.compile(
    r"<!--.*?-->"                      # комментарий
    r"|<!\[CDATA\[.*?\]\]>"            # CDATA
    r"|<!DOCTYPE[^>[]*(?:\[[^]]*\])?>" # DOCTYPE, возможно с описанием сущностей
    r"|<\?[^>]*\?>"                    # <?xml ...?>
    r"|</\s*([\w:.-]+)\s*>"            # закрывающий тег
    r"|<([\w:.-]+)((?:\s+[\w:.-]+\s*=\s*(?:\"[^\"]*\"|'[^']*'))*)\s*(/?)>",
    re.DOTALL)

# Разрядность округления по атрибутам. Координаты листа (COORD) — это
# единицы чертежа шириной около 510, десятой доли хватает с запасом. А вот
# `transform` округлять так же нельзя: в `matrix(.1198 0 0 .1198 …)` первые
# четыре числа — не координаты, а масштаб, и `.1198 → .1` растянуло бы
# вставку в полтора раза.
COORD = ("points", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r",
         "rx", "ry", "width", "height", "stroke-dasharray")
FINE = ("transform", "stroke-width", "font-size", "stroke-miterlimit",
        "gradienttransform", "offset", "stop-opacity", "opacity",
        "fill-opacity", "stroke-opacity")
GEOM = COORD + FINE
ND_COORD = 1
ND_FINE = 4
# Иллюстраторская служебка: в картинке не участвует.
DROP_EL = ("metadata", "i:pgf", "i:aipgf", "foreignobject")
DROP_ATTR_PREFIX = ("i:", "xmlns:i", "xmlns:x", "xmlns:graph", "xml:space",
                    "enable-background", "data-name", "sketch:")


def fmt(v, nd=ND_COORD):
    """Число как можно короче: `.5` вместо `0.500`, `12` вместо `12.00`."""
    s = ("%.*f" % (nd, v)).rstrip("0").rstrip(".")
    if s in ("", "-", "-0", "0"):
        return "0"
    if s.startswith("0."):
        s = s[1:]
    elif s.startswith("-0."):
        s = "-" + s[2:]
    return s


def round_nums(s, nd=ND_COORD):
    out, end = [], 0
    for m in NUM.finditer(s):
        out.append(s[end:m.start()])
        out.append(fmt(float(m.group()), nd))
        end = m.end()
    out.append(s[end:])
    return "".join(out)


# --------------------------------------------------------------- `d` пути --

# Число аргументов у команды пути. У `a`/`A` пятый и шестой аргументы — не
# числа, а флаги: один знак каждый.
PATH_ARGS = {"m": 2, "l": 2, "h": 1, "v": 1, "c": 6, "s": 4,
             "q": 4, "t": 2, "a": 7, "z": 0}
PATH_NUM = re.compile(r"[+-]?(?:\d*\.\d+|\d+\.?)(?:[eE][+-]?\d+)?")
PATH_SEP = re.compile(r"[\s,]*")


def parse_path(d):
    """`d` в список [(команда, [аргументы]), …].

    Разбирать обязательно по-настоящему, а не менять числа регулярным
    выражением: у дуги флаги пишутся слитно с тем, что идёт следом, и
    `a5.763 5.763 0 11.002 11.526` — это не «11.002», а два флага и `.002`.
    Замена «11.002» на округлённое «11» превращает окружность в кляксу, и
    заметно это только глазами, на готовом чертеже.
    """
    out, i, n, cmd = [], 0, len(d), None
    while i < n:
        i = PATH_SEP.match(d, i).end()
        if i >= n:
            break
        ch = d[i]
        if ch.isalpha():
            cmd = ch
            i += 1
            if cmd.lower() == "z":
                out.append((cmd, []))
                cmd = "m" if cmd == "z" else "M"   # после z продолжения быть не может
                continue
        elif cmd is None:
            return None                            # мусор в начале — не трогаем
        if cmd is None:
            return None
        low = cmd.lower()
        if low not in PATH_ARGS:
            return None
        need = PATH_ARGS[low]
        args = []
        for k in range(need):
            i = PATH_SEP.match(d, i).end()
            if low == "a" and k in (3, 4):         # флаги: ровно один знак
                if i < n and d[i] in "01":
                    args.append(float(d[i]))
                    i += 1
                    continue
                return None
            m = PATH_NUM.match(d, i)
            if not m:
                return None
            args.append(float(m.group()))
            i = m.end()
        out.append((cmd, args))
        if cmd == "M":
            cmd = "L"
        elif cmd == "m":
            cmd = "l"
    return out


# Какие аргументы команды — координаты: (индекс x, индекс y), …
COORD_ARGS = {"m": [(0, 1)], "l": [(0, 1)], "t": [(0, 1)],
              "c": [(0, 1), (2, 3), (4, 5)], "s": [(0, 1), (2, 3)],
              "q": [(0, 1), (2, 3)], "a": [(5, 6)], "h": [], "v": [], "z": []}


def to_absolute(items):
    """Привести все команды к абсолютным координатам."""
    out, cx, cy, sx, sy = [], 0.0, 0.0, 0.0, 0.0
    for cmd, args in items:
        low = cmd.lower()
        rel = cmd.islower()
        a = list(args)
        if low == "z":
            out.append(("Z", []))
            cx, cy = sx, sy
            continue
        if low == "h":
            a[0] = cx + a[0] if rel else a[0]
            cx = a[0]
        elif low == "v":
            a[0] = cy + a[0] if rel else a[0]
            cy = a[0]
        else:
            if rel:
                for ix, iy in COORD_ARGS[low]:
                    a[ix] += cx
                    a[iy] += cy
            ix, iy = COORD_ARGS[low][-1]
            cx, cy = a[ix], a[iy]
            if low == "m":
                sx, sy = cx, cy
        out.append((cmd.upper(), a))
    return out


def write_best(items, nd=ND_COORD):
    """Записать путь, выбирая на каждой команде короткую запись.

    В чертеже рядом стоящие точки отличаются на единицы, а не на сотни,
    поэтому относительная запись (`l2.3-1.1`) почти всегда короче
    абсолютной (`L214.7 338.2`). Выбор делается посимвольно: посчитать обе
    записи и взять ту, что вышла короче.
    """
    out, prev, last_cmd = [], "", ""
    cx = cy = sx = sy = 0.0
    for cmd, args in items:
        low = cmd.lower()
        if low == "z":
            out.append("Z")
            prev, last_cmd = "Z", "Z"
            cx, cy = sx, sy
            continue
        rel = list(args)
        if low == "h":
            rel[0] = args[0] - cx
        elif low == "v":
            rel[0] = args[0] - cy
        else:
            for ix, iy in COORD_ARGS[low]:
                rel[ix] = args[ix] - cx
                rel[iy] = args[iy] - cy
        cand = []
        for letter, vals in ((cmd, args), (cmd.lower(), rel)):
            body = _args_str(letter, vals, nd, prev if letter == last_cmd else letter)
            head = "" if letter == last_cmd and letter.lower() != "m" else letter
            cand.append((len(head) + len(body), head, body, letter))
        cand.sort(key=lambda c: c[0])
        _, head, body, letter = cand[0]
        out.append(head + body)
        prev = (head + body)[-1]
        last_cmd = letter
        if low == "h":
            cx = args[0]
        elif low == "v":
            cy = args[0]
        else:
            ix, iy = COORD_ARGS[low][-1]
            cx, cy = args[ix], args[iy]
            if low == "m":
                sx, sy = cx, cy
    return "".join(out)


def _args_str(cmd, args, nd, prev):
    low = cmd.lower()
    out, p = [], prev
    for k, v in enumerate(args):
        if low == "a" and k in (3, 4):
            s = "1" if v else "0"
            if p:
                out.append(" ")
            out.append(s)
            p = s
            continue
        s = fmt(v, nd + 1 if (low == "a" and k < 2) else nd)
        if low == "a" and k == 5:
            if s[0] != "-":
                out.append(" ")
        elif p and p[-1].isdigit():
            if s[0] == "-":
                pass
            elif s[0] == "." and "." in p:
                pass
            else:
                out.append(" ")
        out.append(s)
        p = s
    return "".join(out)


def tighten_path(d):
    """Пережать `d`; если разобрать не удалось — вернуть как есть."""
    items = parse_path(d)
    if items is None:
        return re.sub(r"\s+", " ", d).strip()
    return write_best(to_absolute(items))


def nums(s):
    return [float(x) for x in NUM.findall(s or "")]


def to_path(name, attrs):
    """Геометрия примитива как `d`; None — если такой элемент не переводим."""
    if name == "line":
        x1, y1 = attrs.get("x1", "0"), attrs.get("y1", "0")
        x2, y2 = attrs.get("x2", "0"), attrs.get("y2", "0")
        ax, ay = float(x1), float(y1)
        return "M%s %sl%s %s" % (fmt(ax), fmt(ay),
                                 fmt(float(x2) - ax), fmt(float(y2) - ay))
    if name in ("polyline", "polygon"):
        p = nums(attrs.get("points", ""))
        if len(p) < 4:
            return None
        d = "M" + " ".join(fmt(v) for v in p)
        return d + "z" if name == "polygon" else d
    if name == "path":
        return attrs.get("d", "")   # уже пережат в _clean_attrs
    return None


class _El:
    __slots__ = ("name", "attrs", "kids", "text", "raw")

    def __init__(self, name, attrs):
        self.name, self.attrs, self.kids, self.text, self.raw = name, attrs, [], "", None


def _parse(svg):
    """Разбор в дерево. Всё незнакомое сохраняется как есть."""
    root = _El("#doc", {})
    stack = [root]
    pos = 0
    for m in TOKEN.finditer(svg):
        text = svg[pos:m.start()]
        pos = m.end()
        if text.strip():
            stack[-1].kids.append(text)
        tok = m.group(0)
        if m.group(1):                                  # закрывающий
            name = m.group(1).lower()
            for i in range(len(stack) - 1, 0, -1):
                if stack[i].name == name:
                    del stack[i:]
                    break
            continue
        if m.group(2) is None:                          # комментарий, DOCTYPE, <?xml?>
            continue
        name = m.group(2).lower()
        attrs = {}
        for k, v in ATTR.findall(m.group(3) or ""):
            attrs[k.lower()] = v[1:-1]
        el = _El(name, attrs)
        stack[-1].kids.append(el)
        if not m.group(4):
            stack.append(el)
    return root


def _clean_attrs(attrs):
    out = {}
    for k, v in attrs.items():
        if any(k.startswith(p) for p in DROP_ATTR_PREFIX):
            continue
        if k == "d":
            v = tighten_path(v)
        elif k in COORD:
            v = round_nums(v, ND_COORD)
        elif k in FINE:
            v = round_nums(v, ND_FINE)
        out[k] = v
    return out


# Примитивы, которые переводятся в `<path>` один в один.
SHAPES = ("line", "polyline", "polygon", "path")
# Геометрия: в оформление не идёт.
SHAPE_GEOM = ("d", "points", "x1", "y1", "x2", "y2")
# Атрибуты, которые остаются при элементе как есть: их нельзя ни слить в
# класс (`style` и `class` — это не пары «свойство: значение»), ни потерять.
KEEP_ATTR = ("class", "style", "clip-path", "clip-rule", "transform",
             "id", "mask", "filter", "marker-start", "marker-mid",
             "marker-end", "opacity")


def _split_style(attrs):
    """Разложить атрибуты на «оставить при элементе» и «вынести в класс»."""
    keep, fold = {}, {}
    for a, v in attrs.items():
        if a in SHAPE_GEOM:
            continue
        (keep if a in KEEP_ATTR else fold)[a] = v
    return keep, fold


def _mergeable(attrs):
    """Можно ли слить этот контур с соседним.

    Только незалитые. Два залитых контура в одном `d` — это уже не две
    фигуры, а одна с дыркой: по правилу заливки общая часть выпадает, и
    белая плашка, которой чертёж закрывает то, что за ней, перестаёт
    закрывать. На чертеже это видно сразу — сквозь бак проступают болты
    задней стенки.
    """
    fill = (attrs.get("fill") or "").strip().lower()
    if fill != "none":
        return False
    return "fill-rule" not in attrs and "clip-rule" not in attrs


def _escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class _Writer:
    def __init__(self, nd=2, image_scale=2.0, image_quality=78):
        self.styles = {}      # набор атрибутов оформления -> имя класса
        self.order = []
        self.nd = nd
        self.image_scale = image_scale
        self.image_quality = image_quality
        self.texts = []       # (строка, x, y, font-size, scale_x)

    def path_tag(self, keep, fold, d):
        """`<path>` с вынесенным в класс оформлением."""
        attrs = dict(keep)
        if fold:
            key = ";".join("%s:%s" % (a, v) for a, v in sorted(fold.items()))
            name = self.cls(key)
            attrs["class"] = (attrs["class"] + " " + name) if attrs.get("class") else name
        a = "".join(' %s="%s"' % (n, v.replace('"', "&quot;")) for n, v in attrs.items())
        return '<path%s d="%s"/>' % (a, d)

    def cls(self, key):
        if key not in self.styles:
            self.styles[key] = "a%d" % len(self.styles)
            self.order.append(key)
        return self.styles[key]

    # --- растровая вставка ---------------------------------------------------
    def shrink_image(self, attrs, scale):
        """Пережать base64-картинку под её показываемый размер."""
        href = attrs.get("xlink:href") or attrs.get("href") or ""
        if not href.startswith("data:image/"):
            return attrs
        try:
            from PIL import Image
        except ImportError:
            return attrs
        try:
            head, b64 = href.split(",", 1)
            blob = base64.b64decode(b64)
            im = Image.open(io.BytesIO(blob))
            shown_w = float(attrs.get("width", im.width)) * scale
            # Ширина показа с запасом под увеличение, но выше 2400 px
            # смысла нет: столько на экране всё равно не разглядеть, а в
            # файл это ложится мегабайтами.
            target = max(64, min(2400, int(shown_w * self.image_scale)))
            if target >= im.width:
                return attrs
            ratio = target / im.width
            im = im.resize((target, max(1, int(im.height * ratio))), Image.LANCZOS)
            buf = io.BytesIO()
            alpha = im.mode in ("RGBA", "LA", "P") and "transparency" in im.info
            if alpha or im.mode in ("RGBA", "LA"):
                im.save(buf, "PNG", optimize=True)
                mime = "image/png"
            else:
                im.convert("RGB").save(buf, "JPEG", quality=self.image_quality,
                                       optimize=True, progressive=True)
                mime = "image/jpeg"
            if buf.tell() >= len(blob):
                return attrs
            attrs = dict(attrs)
            new = "data:%s;base64,%s" % (mime, base64.b64encode(buf.getvalue()).decode())
            # исходный размер остаётся: transform пересчитывать не нужно,
            # потому что width/height задают систему координат картинки.
            if "xlink:href" in attrs:
                attrs["xlink:href"] = new
            else:
                attrs["href"] = new
            return attrs
        except Exception:
            return attrs

    # --- текст ---------------------------------------------------------------
    def note_text(self, el, scale):
        """Запомнить, где стоит номер позиции: из этого выйдут выноски."""
        def collect(e):
            s = ""
            for k in e.kids:
                s += k if isinstance(k, str) else collect(k)
            return s
        label = re.sub(r"\s+", "", collect(el))
        if not label:
            return
        fs = nums(el.attrs.get("font-size", ""))
        size = fs[0] if fs else 10.0
        sx = 1.0
        tr = el.attrs.get("transform", "")
        x = y = None
        if tr.startswith("matrix"):
            v = nums(tr)
            if len(v) >= 6:
                sx, x, y = v[0] or 1.0, v[4], v[5]
        elif tr.startswith("translate"):
            v = nums(tr)
            if len(v) >= 2:
                x, y = v[0], v[1]
        if x is None:
            x = float(nums(el.attrs.get("x", "0"))[0]) if el.attrs.get("x") else None
            y = float(nums(el.attrs.get("y", "0"))[0]) if el.attrs.get("y") else None
        if x is None or y is None:
            return
        self.texts.append((label, x, y, size, abs(sx) or 1.0))

    # --- обход ---------------------------------------------------------------
    def emit(self, el, out, scale=1.0):
        kids = el.kids
        i = 0
        while i < len(kids):
            k = kids[i]
            if isinstance(k, str):
                out.append(_escape(k) if el.name in ("text", "tspan") else k)
                i += 1
                continue
            if k.name in DROP_EL:
                i += 1
                continue
            if k.name.startswith("i:"):          # обёртка Illustrator: содержимое оставляем
                self.emit(k, out, scale)
                i += 1
                continue
            attrs = _clean_attrs(k.attrs)
            d = to_path(k.name, attrs) if k.name in SHAPES else None
            if d is not None:
                keep, fold = _split_style(attrs)
                run = [d]
                j = i + 1
                if _mergeable(attrs):
                    while j < len(kids):
                        n = kids[j]
                        if isinstance(n, str) and not n.strip():
                            j += 1
                            continue
                        if not isinstance(n, _El) or n.name not in SHAPES:
                            break
                        na = _clean_attrs(n.attrs)
                        if not _mergeable(na):
                            break
                        nd_ = to_path(n.name, na)
                        if nd_ is None:
                            break
                        nkeep, nfold = _split_style(na)
                        if nkeep != keep or nfold != fold:
                            break
                        run.append(nd_)
                        j += 1
                out.append(self.path_tag(keep, fold, tighten_path("".join(run))))
                i = j
                continue
            if k.name == "image":
                attrs = self.shrink_image(attrs, scale * _scale_of(attrs.get("transform", "")))
            if k.name == "text":
                self.note_text(k, scale)
            sub = []
            if k.kids:
                self.emit(k, sub, scale * _scale_of(attrs.get("transform", "")))
            body = "".join(sub)
            a = "".join(' %s="%s"' % (n, v.replace('"', "&quot;")) for n, v in attrs.items())
            if body:
                out.append("<%s%s>%s</%s>" % (k.name, a, body, k.name))
            else:
                out.append("<%s%s/>" % (k.name, a))
            i += 1


def _scale_of(transform):
    """Во сколько раз этот `transform` растягивает по горизонтали.

    Преобразований в атрибуте может быть несколько и в любом порядке
    (`translate(…) scale(…)`), поэтому смотреть надо на все, а не на
    первое: из-за этого недосмотра растровая вставка шириной 9697 px,
    показанная в чертеже в шесть раз мельче, оставалась во всю величину —
    5,5 МБ на один лист.
    """
    if not transform:
        return 1.0
    k = 1.0
    for name, body in re.findall(r"([a-zA-Z]+)\s*\(([^)]*)\)", transform):
        v = nums(body)
        low = name.lower()
        if low == "matrix" and len(v) >= 4:
            k *= abs(v[0]) or 1.0
        elif low == "scale" and v:
            k *= abs(v[0]) or 1.0
    return k or 1.0


def optimize(svg, callouts=None, image_scale=2.0):
    """Вернуть (сжатый svg, ширина, высота, выноски).

    `callouts` — номера позиций этого узла. Текст на чертеже становится
    выноской, только если он совпадает с номером из таблицы: подписи
    размеров и пояснения выносками не являются.
    """
    doc = _parse(svg)
    root = None
    for k in doc.kids:
        if isinstance(k, _El) and k.name == "svg":
            root = k
            break
    if root is None:
        return svg, 0.0, 0.0, []

    box = root.attrs.get("viewbox") or root.attrs.get("viewBox")
    if box:
        v = nums(box)
        w, h = (v[2], v[3]) if len(v) >= 4 else (0.0, 0.0)
    else:
        w = float(nums(root.attrs.get("width", "0"))[0] or 0)
        h = float(nums(root.attrs.get("height", "0"))[0] or 0)

    wr = _Writer(image_scale=image_scale)
    body = []
    wr.emit(root, body, 1.0)

    head = '<svg xmlns="http://www.w3.org/2000/svg"'
    if "xmlns:xlink" in root.attrs or "xlink:href" in "".join(body):
        head += ' xmlns:xlink="http://www.w3.org/1999/xlink"'
    head += ' viewBox="0 0 %s %s">' % (fmt(w, 2), fmt(h, 2))
    css = "".join(".%s{%s}" % (wr.styles[k], k) for k in wr.order if k)
    out = head + ("<style>%s</style>" % css if css else "") + "".join(body) + "</svg>"

    spots = []
    want = set(str(c) for c in (callouts or []))
    for label, x, y, size, sx in wr.texts:
        if want and label not in want:
            continue
        # ширина цифры Arial — примерно 0,56 кегля; прямоугольник чуть шире,
        # чтобы в него было легко попасть пальцем.
        cw = 0.56 * size * sx
        x1 = x - 0.15 * cw
        x2 = x + cw * (len(label) + 0.3)
        y1 = y - size * 0.85
        y2 = y + size * 0.25
        spots.append([label, round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)])
    return out, w, h, spots
