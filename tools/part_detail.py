"""Parser for the EPC part detail page (/part/<partNO>/<parentPartNO>).

The page is server-rendered: attributes live in a <ol> of label/value pairs,
photos in #thumbnails, and related data (supersession, kits, ...) in tabs.
"""
import re

TAG_RE = re.compile(r"<[^>]+>")
LI_RE = re.compile(r"<li>\s*<span>\s*(?P<label>.*?)\s*[：:]\s*</span>\s*(?P<value>.*?)</li>",
                   re.DOTALL)

# Labels as rendered by the EPC in zh_CN / en_US.
FIELD_MAP = {
    "配件编码": "partNO", "Part Number": "partNO",
    "配件名称": "partName", "Part Name": "partName",
    "规格": "spec", "Specification": "spec",
    "重量(KG)": "weightKg", "Weight(KG)": "weightKg",
    "尺寸(mm)": "sizeMm", "Size(mm)": "sizeMm",
    "最小包装单元": "mpq", "Minimum Package Quantity": "mpq",
    "成交折扣组": "discountGroup",
    "是否保养件": "isMaintenance", "是否易损件": "isWear",
    "是否特殊采购件": "isSpecialPurchase",
    "储备建议": "stockAdvice", "单位": "unit", "Unit": "unit",
    "配件备注": "note",
}


def _text(html):
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", html)).strip()


COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def parse(html):
    """Extracts the part card: attributes, photo URLs, parent part."""
    out = {"attrs": {}, "attrsRaw": {}, "photos": []}
    html = COMMENT_RE.sub("", html)  # the real <img> src is the obfuscated
    # token next to it; the human-readable filename only lives in a comment.

    detail = html[html.find('<div class="detail">'):]
    for m in LI_RE.finditer(detail[:detail.find('<div class="detail-select">')] or detail):
        label = _text(m.group("label"))
        value = _text(m.group("value"))
        out["attrsRaw"][label] = value
        key = FIELD_MAP.get(label)
        if key:
            out["attrs"][key] = value

    # dimensions render as "2056.0* 1858.0* 1517.0"
    size = out["attrs"].get("sizeMm")
    if size:
        dims = [d for d in (p.strip() for p in size.split("*")) if d]
        out["attrs"]["sizeMm"] = "*".join(dims)

    for m in re.finditer(r'<ul id="thumbnails">(.*?)</ul>', html, re.DOTALL):
        for src in re.finditer(r'src="([^"]+)"', m.group(1)):
            out["photos"].append(src.group(1))
    main = re.search(r'id="thumbnails-img"[^>]*', html)
    if main:
        src = re.search(r'src="([^"]+)"', main.group(0))
        data_img = re.search(r'data-img="([^"]+)"', main.group(0))
        if src and data_img and data_img.group(1) != "nopic":
            out["photos"].insert(0, src.group(1))

    parent = re.search(r'id="detail-parentPartNO"[^>]*>([^<]*)<', html)
    if parent:
        out["parentPartNO"] = parent.group(1).strip()
    return out
