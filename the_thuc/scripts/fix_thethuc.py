#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_thethuc.py — Tự động SỬA các lỗi thể thức phát hiện được rồi xuất .docx mới.

    python fix_thethuc.py VANBAN.docx --out VANBAN_daSua.docx [--spec spec.json]

Bộ sửa chỉ tác động lên các phần tử ĐÃ NHẬN DIỆN và đang báo LỖI (auto):
  - đặt phông Times New Roman, màu đen;
  - kẹp cỡ chữ về đúng khoảng cho phép;
  - đặt đậm/nghiêng theo quy định;
  - bật in hoa (w:caps) cho phần tử yêu cầu IN HOA mà chưa in hoa.
Không tự động viết hoa lại nội dung văn bản, không đụng tới các mục "rà thủ công".
Mọi phần khác của tệp được giữ nguyên (ảnh, header/footer, quan hệ...).
"""
import argparse
import json
import os
import shutil
import zipfile
from lxml import etree

import sys
sys.path.insert(0, os.path.dirname(__file__))
from docx_format import DocxFormat, q, qa, W, V, A
import check_thethuc as C

# thứ tự con hợp lệ trong <w:rPr> (rút gọn, đủ cho các trường ta chỉnh)
RPR_ORDER = ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps",
             "strike", "dstrike", "color", "spacing", "sz", "szCs", "lang"]


def _child(rpr, name):
    el = rpr.find(q(name))
    if el is None:
        el = etree.SubElement(rpr, q(name))
    return el


def _reorder(rpr):
    order = {n: i for i, n in enumerate(RPR_ORDER)}
    children = list(rpr)
    children.sort(key=lambda e: order.get(etree.QName(e).localname, 99))
    for c in children:
        rpr.remove(c)
    for c in children:
        rpr.append(c)


def set_run_format(r_el, font=None, size_pt=None, bold=None, italic=None,
                   caps=None, color="000000"):
    rpr = r_el.find(q("rPr"))
    if rpr is None:
        rpr = etree.Element(q("rPr"))
        r_el.insert(0, rpr)
    if font is not None:
        rf = _child(rpr, "rFonts")
        for a in ("ascii", "hAnsi", "cs"):
            rf.set(q(a), font)
    if size_pt is not None:
        val = str(int(round(size_pt * 2)))
        _child(rpr, "sz").set(q("val"), val)
        _child(rpr, "szCs").set(q("val"), val)
    if bold is not None:
        b = _child(rpr, "b")
        b.set(q("val"), "true" if bold else "false")
    if italic is not None:
        i = _child(rpr, "i")
        i.set(q("val"), "true" if italic else "false")
    if caps:
        _child(rpr, "caps").set(q("val"), "true")
    if color is not None:
        _child(rpr, "color").set(q("val"), color)
    _reorder(rpr)


def clamp_size(cur, lo, hi):
    if cur is None:
        return hi          # mặc định lấy cỡ lớn nhất cho phép
    if cur < lo:
        return lo
    if cur > hi:
        return hi
    return cur


def fix_dashes(doc):
    """Thay mọi gạch dài '–' (en) / '—' (em) bằng gạch nối thường '-' trong toàn văn bản."""
    n = 0
    for t in doc._doc.iter(q("t")):
        if t.text and ("\u2013" in t.text or "\u2014" in t.text):
            new = t.text.replace("\u2013", "-").replace("\u2014", "-")
            if new != t.text:
                n += new and (t.text.count("\u2013") + t.text.count("\u2014"))
                t.text = new
    return n


def _set_vml_weight(shp, pt="0.75pt"):
    shp.set("strokeweight", pt)
    st = shp.find("{%s}stroke" % V)
    if st is not None and st.get("weight") is not None:
        st.set("weight", pt)


def _set_drawingml_weight(el, emu="9525"):
    """el là <a:ln> hoặc phần tử <w:drawing>. Đặt độ rộng nét = 0,75pt (9525 EMU)."""
    if el.tag == qa("ln"):
        el.set("w", emu)
        return True
    ln = None
    for d in el.iter():
        if isinstance(d.tag, str) and d.tag == qa("ln"):
            ln = d
            break
    if ln is not None:
        ln.set("w", emu)
        return True
    # chưa có <a:ln>: chèn vào spPr nếu tìm thấy
    for d in el.iter():
        if isinstance(d.tag, str) and d.tag.split("}")[-1] == "spPr":
            ln = etree.SubElement(d, qa("ln"))
            ln.set("w", emu)
            return True
    return False


def fix_lines(doc, det, spec):
    """Ép nét đường kẻ ngang (shape) dưới Tiêu ngữ / tên cơ quan / trích yếu về 0,75pt.
    KHÔNG tạo mới đường kẻ và KHÔNG đổi độ dài (rủi ro layout) — chỉ chỉnh nét shape sẵn có."""
    keys = [it for it in spec["mau_chu"] if it.get("kiem_tra") == "duong_ke"]
    fixed = 0
    for item in keys:
        anchor = det.found.get(item.get("duoi"))
        if anchor is None or anchor.index is None:
            continue
        shapes, _ = doc.lines_near(anchor.index, lookahead=2)
        for s in shapes:
            if s["weight_pt"] is not None and abs(s["weight_pt"] - 0.75) <= 0.06:
                continue
            if s["kind"] == "vml":
                _set_vml_weight(s["el"])
                fixed += 1
            else:
                if _set_drawingml_weight(s["el"]):
                    fixed += 1
    return fixed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docx")
    ap.add_argument("--out", required=True)
    ap.add_argument("--spec", default=os.path.join(
        os.path.dirname(__file__), "..", "reference", "nd30_spec.json"))
    args = ap.parse_args()

    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    spec_by_key = {it["key"]: it for it in spec["mau_chu"]}

    doc = DocxFormat(args.docx)
    results, det = C.run_checks(doc, spec)

    # gom các paragraph cần sửa: key -> list[xml element]
    targets = {}  # id(p_el) -> spec
    def add_target(para, item):
        if para is None or para.index is None:
            return
        el = doc.p_elements[para.index]
        targets[id(el)] = (el, item)

    fixed_keys = []
    for res in results["mau_chu"]:
        if res["status"] != "loi" or not res.get("auto"):
            continue
        key = res["key"]
        item = spec_by_key.get(key)
        if not item:
            continue
        para = det.found.get(key)
        if key == "noi_nhan_ds":
            for p in getattr(det, "noi_nhan_block", []):
                add_target(p, item)
        else:
            add_target(para, item)
        fixed_keys.append(key)

    # áp dụng sửa
    for el, item in targets.values():
        lo = hi = None
        if item.get("co_chu"):
            lo, hi = item["co_chu"]["min"], item["co_chu"]["max"]
        bold = item.get("dam")
        dang = item.get("dang")
        italic = True if dang == "nghieng" else (False if dang == "dung" else None)
        caps = (item.get("loai_chu") == "in_hoa")
        for r_el in el.iter(q("r")):
            # bỏ qua run rỗng (chỉ chứa ảnh/đối tượng)
            has_text = any(t.tag in (q("t"), q("delText")) for t in r_el.iter())
            if not has_text:
                continue
            # xác định cỡ hiện tại để kẹp
            cur = None
            rpr = r_el.find(q("rPr"))
            if rpr is not None:
                sz = rpr.find(q("sz"))
                if sz is not None and sz.get(q("val")):
                    cur = int(sz.get(q("val"))) / 2.0
            size_pt = clamp_size(cur, lo, hi) if lo is not None else None
            set_run_format(r_el, font="Times New Roman", size_pt=size_pt,
                           bold=bold, italic=italic,
                           caps=caps if caps else None, color="000000")

    # sửa dấu gạch dài -> gạch nối thường (toàn văn bản)
    n_dash = fix_dashes(doc)
    # ép nét đường kẻ shape (Tiêu ngữ / tên cơ quan / trích yếu) về 0,75pt
    n_line = fix_lines(doc, det, spec)

    # ghi document.xml đã sửa vào bản sao của tệp gốc (giữ nguyên các phần khác)
    new_doc_xml = etree.tostring(doc._doc, xml_declaration=True,
                                 encoding="UTF-8", standalone=True)
    tmp = args.out + ".tmp"
    with zipfile.ZipFile(args.docx) as zin, \
         zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = new_doc_xml
            zout.writestr(item, data)
    shutil.move(tmp, args.out)

    extra = []
    if n_dash:
        extra.append(f"{n_dash} gạch dài→'-'")
    if n_line:
        extra.append(f"{n_line} đường kẻ→0,75pt")
    tail = (" | " + ", ".join(extra)) if extra else ""
    print(f"Đã sửa {len(targets)} đoạn, các thành phần: {', '.join(sorted(set(fixed_keys))) or '(không có lỗi auto)'}{tail}")
    print("→", args.out)


if __name__ == "__main__":
    main()
