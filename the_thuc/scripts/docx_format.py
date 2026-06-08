#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docx_format.py — Đọc .docx và phân giải định dạng HIỆU LỰC của từng run
(font, cỡ chữ, đậm, nghiêng, in hoa, màu) theo chuỗi kế thừa:
    run rPr  ->  paragraph style (theo basedOn)  ->  docDefaults.

Trả về danh sách Paragraph, mỗi paragraph có: text, alignment (jc),
spacing, indent, và danh sách Run đã phân giải.

Dùng cho việc kiểm tra thể thức văn bản hành chính theo NĐ 30/2020/NĐ-CP.
"""
import zipfile
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
V = "urn:schemas-microsoft-com:vml"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
WPS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
NS = {"w": W}

EMU_PER_PT = 12700.0  # 1pt = 12700 EMU


def q(tag):
    return f"{{{W}}}{tag}"


def qv(tag):
    return f"{{{V}}}{tag}"


def qa(tag):
    return f"{{{A}}}{tag}"


def qwp(tag):
    return f"{{{WP}}}{tag}"


def _emu_to_pt(v):
    try:
        return round(float(v) / EMU_PER_PT, 2)
    except (TypeError, ValueError):
        return None


def _vml_measure_to_pt(s):
    """Chuyển một số đo VML/CSS ('0.75pt', '1pt', '12px', '2cm', '36') sang pt."""
    if s is None:
        return None
    s = str(s).strip().lower()
    import re as _re
    m = _re.match(r"^([0-9]*\.?[0-9]+)\s*(pt|px|pc|in|cm|mm|em)?$", s)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2) or "pt"
    factor = {"pt": 1.0, "px": 0.75, "pc": 12.0, "in": 72.0,
              "cm": 28.3465, "mm": 2.83465, "em": 12.0}.get(unit, 1.0)
    return round(val * factor, 2)


def estimate_text_width_pt(text, size_pt):
    """Ước lượng bề rộng hiển thị của một dòng chữ Times New Roman (pt).
    Dấu phụ tiếng Việt không cộng bề rộng (nằm trên chữ nền) nên bỏ qua khi đếm."""
    import unicodedata
    if not text or not size_pt:
        return None
    wide = set("MWQGOD@%")
    narrow = set("iljtfI.,;:'!|()[]/\\ ")
    total = 0.0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        if ch == " ":
            total += 0.26
        elif ch in wide or (ch.isalpha() and ch.isupper()):
            total += 0.62
        elif ch in narrow:
            total += 0.30
        else:
            total += 0.50
    return round(total * size_pt, 1)


def _toggle(el):
    """Đọc thuộc tính bật/tắt kiểu <w:b/>, <w:b w:val="0"/>. Trả True/False/None."""
    if el is None:
        return None
    val = el.get(q("val"))
    if val is None:
        return True
    return val not in ("0", "false", "off", "none")


def _read_rpr(rpr):
    """Bóc các trường định dạng từ một phần tử <w:rPr>. Giá trị None = không khai báo."""
    out = {"font": None, "size": None, "bold": None, "italic": None,
           "caps": None, "color": None}
    if rpr is None:
        return out
    rf = rpr.find(q("rFonts"))
    if rf is not None:
        out["font"] = rf.get(q("ascii")) or rf.get(q("hAnsi")) or rf.get(q("cs"))
    sz = rpr.find(q("sz"))
    if sz is not None and sz.get(q("val")):
        try:
            out["size"] = int(sz.get(q("val"))) / 2.0  # half-point -> pt
        except ValueError:
            pass
    if out["size"] is None:
        szcs = rpr.find(q("szCs"))
        if szcs is not None and szcs.get(q("val")):
            try:
                out["size"] = int(szcs.get(q("val"))) / 2.0
            except ValueError:
                pass
    out["bold"] = _toggle(rpr.find(q("b")))
    out["italic"] = _toggle(rpr.find(q("i")))
    out["caps"] = _toggle(rpr.find(q("caps")))
    col = rpr.find(q("color"))
    if col is not None:
        out["color"] = col.get(q("val"))
    return out


def _merge(base, over):
    """Ghi đè base bằng over với các trường khác None."""
    r = dict(base)
    for k, v in over.items():
        if v is not None:
            r[k] = v
    return r


class Run:
    def __init__(self, text, fmt):
        self.text = text
        self.font = fmt["font"]
        self.size = fmt["size"]
        self.bold = bool(fmt["bold"]) if fmt["bold"] is not None else False
        self.italic = bool(fmt["italic"]) if fmt["italic"] is not None else False
        self.caps = bool(fmt["caps"]) if fmt["caps"] is not None else False
        self.color = fmt["color"]

    @property
    def display(self):
        return self.text.upper() if self.caps else self.text


class Paragraph:
    def __init__(self, runs, align, spacing, indent, style_id, in_header=False, index=None):
        self.runs = runs
        self.align = align            # left/center/right/both/None
        self.spacing = spacing        # dict line/lineRule/before/after
        self.indent = indent          # dict firstLine/hanging/left
        self.style_id = style_id
        self.in_header = in_header
        self.index = index            # vị trí trong document order (cho bộ sửa)

    @property
    def text(self):
        return "".join(r.text for r in self.runs)

    @property
    def display_text(self):
        return "".join(r.display for r in self.runs)

    @property
    def is_empty(self):
        return self.text.strip() == ""

    def dominant_run(self):
        """Run có nhiều ký tự không-trắng nhất (đại diện định dạng của dòng)."""
        best, score = None, -1
        for r in self.runs:
            s = len(r.text.strip())
            if s > score:
                best, score = r, s
        return best


class DocxFormat:
    def __init__(self, path):
        self.path = path
        with zipfile.ZipFile(path) as z:
            self._doc = etree.fromstring(z.read("word/document.xml"))
            try:
                self._styles = etree.fromstring(z.read("word/styles.xml"))
            except KeyError:
                self._styles = None
            self._headers = []
            for name in z.namelist():
                if name.startswith("word/header") and name.endswith(".xml"):
                    self._headers.append(etree.fromstring(z.read(name)))
        self._build_styles()
        self.paragraphs = self._collect_paragraphs()
        self.sectpr = self._doc.find(f".//{q('body')}/{q('sectPr')}")

    # ---- styles ----
    def _build_styles(self):
        self.default_rpr = {"font": None, "size": None, "bold": None,
                            "italic": None, "caps": None, "color": None}
        self.default_align = None
        self.styles = {}        # id -> {rpr, basedOn, align}
        self.default_para_style = None
        if self._styles is None:
            return
        dd = self._styles.find(q("docDefaults"))
        if dd is not None:
            rprd = dd.find(f"{q('rPrDefault')}/{q('rPr')}")
            self.default_rpr = _read_rpr(rprd)
        for st in self._styles.findall(q("style")):
            if st.get(q("type")) != "paragraph":
                continue
            sid = st.get(q("styleId"))
            based = st.find(q("basedOn"))
            rpr = st.find(q("rPr"))
            ppr = st.find(q("pPr"))
            align = None
            if ppr is not None:
                jc = ppr.find(q("jc"))
                if jc is not None:
                    align = jc.get(q("val"))
            self.styles[sid] = {
                "rpr": _read_rpr(rpr),
                "basedOn": based.get(q("val")) if based is not None else None,
                "align": align,
            }
            if st.get(q("default")) == "1":
                self.default_para_style = sid

    def _style_chain(self, sid):
        chain, seen = [], set()
        while sid and sid in self.styles and sid not in seen:
            seen.add(sid)
            chain.append(sid)
            sid = self.styles[sid]["basedOn"]
        return chain  # specific -> base

    def _resolved_style_rpr(self, sid):
        """Gộp rPr theo chuỗi style: base trước, specific ghi đè sau."""
        acc = dict(self.default_rpr)
        for s in reversed(self._style_chain(sid)):
            acc = _merge(acc, self.styles[s]["rpr"])
        return acc

    def _resolved_style_align(self, sid):
        for s in self._style_chain(sid):
            a = self.styles[s].get("align")
            if a:
                return a
        return None

    # ---- paragraphs ----
    def _para_from_el(self, p, in_header=False):
        ppr = p.find(q("pPr"))
        style_id = None
        align = None
        spacing = {}
        indent = {}
        if ppr is not None:
            ps = ppr.find(q("pStyle"))
            if ps is not None:
                style_id = ps.get(q("val"))
            jc = ppr.find(q("jc"))
            if jc is not None:
                align = jc.get(q("val"))
            sp = ppr.find(q("spacing"))
            if sp is not None:
                for a in ("line", "lineRule", "before", "after"):
                    if sp.get(q(a)) is not None:
                        spacing[a] = sp.get(q(a))
            ind = ppr.find(q("ind"))
            if ind is not None:
                for a in ("firstLine", "hanging", "left", "start"):
                    if ind.get(q(a)) is not None:
                        indent[a] = ind.get(q(a))
        if align is None and style_id:
            align = self._resolved_style_align(style_id)
        if align is None:
            align = self.default_align

        style_rpr = self._resolved_style_rpr(style_id) if style_id \
            else dict(self.default_rpr)

        runs = []
        # gồm cả run trong hyperlink
        for r in p.iter(q("r")):
            texts = []
            for t in r.iter():
                if t.tag in (q("t"), q("delText")):
                    texts.append(t.text or "")
                elif t.tag == q("tab"):
                    texts.append("\t")
                elif t.tag in (q("br"), q("cr")):
                    texts.append(" ")
            text = "".join(texts)
            if text == "":
                continue
            rpr = r.find(q("rPr"))
            fmt = _merge(style_rpr, _read_rpr(rpr))
            runs.append(Run(text, fmt))
        return Paragraph(runs, align, spacing, indent, style_id, in_header)

    def _collect_paragraphs(self):
        out = []
        self.p_elements = []
        body = self._doc.find(q("body"))
        if body is not None:
            # bao gồm cả paragraph trong bảng
            for i, p in enumerate(body.iter(q("p"))):
                par = self._para_from_el(p, in_header=False)
                par.index = i
                out.append(par)
                self.p_elements.append(p)
        return out

    def header_paragraphs(self):
        out = []
        for h in self._headers:
            for p in h.iter(q("p")):
                out.append(self._para_from_el(p, in_header=True))
        return out

    # ---- page setup ----
    def page_setup(self):
        info = {"w": None, "h": None, "orient": None,
                "top": None, "bottom": None, "left": None, "right": None,
                "header": None, "footer": None}
        if self.sectpr is None:
            return info
        pg = self.sectpr.find(q("pgSz"))
        if pg is not None:
            info["w"] = _int(pg.get(q("w")))
            info["h"] = _int(pg.get(q("h")))
            info["orient"] = pg.get(q("orient")) or "portrait"
        mar = self.sectpr.find(q("pgMar"))
        if mar is not None:
            for a in ("top", "bottom", "left", "right", "header", "footer"):
                info[a] = _int(mar.get(q(a)))
        return info

    def has_page_number(self):
        """Có trường PAGE trong header/footer không."""
        with zipfile.ZipFile(self.path) as z:
            for name in z.namelist():
                if (name.startswith("word/header") or name.startswith("word/footer")) \
                        and name.endswith(".xml"):
                    blob = z.read(name).decode("utf-8", "ignore")
                    if "PAGE" in blob and "instrText" in blob:
                        return True
        return False

    # ---- đường kẻ ngang (dưới Tiêu ngữ / tên cơ quan) ----
    def graphic_lines_in(self, p_el):
        """Tìm các đường kẻ dạng SHAPE trong một <w:p>.
        Trả list dict: {kind:'vml'|'drawingml', weight_pt, length_pt, el}."""
        out = []
        # --- VML: <w:pict> chứa v:line / v:rect / v:shape ... ---
        for pict in p_el.iter(q("pict")):
            for shp in pict.iter():
                if not isinstance(shp.tag, str) or not shp.tag.startswith("{" + V + "}"):
                    continue
                local = shp.tag.split("}", 1)[1]
                if local not in ("line", "rect", "shape", "roundrect", "polyline", "oval"):
                    continue
                weight = _vml_measure_to_pt(shp.get("strokeweight"))
                if weight is None:
                    st = shp.find(qv("stroke"))
                    if st is not None:
                        weight = _vml_measure_to_pt(st.get("weight"))
                # độ dài: ưu tiên from/to (v:line), rồi style width
                length = None
                frm, to = shp.get("from"), shp.get("to")
                if frm and to:
                    try:
                        x1 = _vml_measure_to_pt(frm.split(",")[0])
                        x2 = _vml_measure_to_pt(to.split(",")[0])
                        if x1 is not None and x2 is not None:
                            length = round(abs(x2 - x1), 1)
                    except Exception:
                        pass
                if length is None:
                    style = shp.get("style") or ""
                    for part in style.split(";"):
                        if part.strip().startswith("width:"):
                            length = _vml_measure_to_pt(part.split(":", 1)[1])
                out.append({"kind": "vml", "weight_pt": weight,
                            "length_pt": length, "el": shp})
        # --- DrawingML: <w:drawing> ---
        for dr in p_el.iter(q("drawing")):
            ext = dr.find(".//" + qwp("extent"))
            length = _emu_to_pt(ext.get("cx")) if ext is not None else None
            ln = dr.find(".//" + qa("ln"))
            weight = _emu_to_pt(ln.get("w")) if (ln is not None and ln.get("w")) else None
            out.append({"kind": "drawingml", "weight_pt": weight,
                        "length_pt": length, "el": (ln if ln is not None else dr)})
        return out

    def para_bottom_border(self, p_el):
        """Đường kẻ kiểu BORDER đáy đoạn (không phải shape). Trả {sz_pt,val} hoặc None."""
        ppr = p_el.find(q("pPr"))
        if ppr is None:
            return None
        pbdr = ppr.find(q("pBdr"))
        if pbdr is None:
            return None
        bot = pbdr.find(q("bottom"))
        if bot is None:
            return None
        sz = bot.get(q("sz"))
        return {"sz_pt": (round(int(sz) / 8.0, 3) if sz and sz.isdigit() else None),
                "val": bot.get(q("val"))}

    def lines_near(self, para_index, lookahead=2):
        """Gom đường kẻ ở đoạn `para_index` và vài đoạn ngay sau (theo document order)."""
        shapes, border = [], None
        for j in range(para_index, min(para_index + 1 + lookahead, len(self.p_elements))):
            pe = self.p_elements[j]
            gl = self.graphic_lines_in(pe)
            if gl:
                shapes.extend(gl)
            if j == para_index or (j > para_index and not self.paragraphs[j].text.strip()):
                b = self.para_bottom_border(pe)
                if b and border is None:
                    border = b
            # dừng nếu gặp đoạn có chữ khác (không phải đoạn kẻ trống)
            if j > para_index and self.paragraphs[j].text.strip() and not gl:
                break
        return shapes, border


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# tiện ích chuyển đổi twips <-> mm
def twips_to_mm(tw):
    return None if tw is None else round(tw / 56.6929, 1)


def mm_to_twips(mm):
    return int(round(mm * 56.6929))
