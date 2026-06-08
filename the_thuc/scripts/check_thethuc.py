#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_thethuc.py — Phát hiện lỗi thể thức văn bản hành chính theo
Phụ lục I Nghị định 30/2020/NĐ-CP và xuất báo cáo HTML mã màu.

    python check_thethuc.py VANBAN.docx [--out THUMUC] [--spec spec.json]

Đầu ra:
    THUMUC/ket_qua.json   – kết quả chi tiết (máy đọc)
    THUMUC/bao_cao.html   – báo cáo rà soát (người đọc, mã màu)

Mọi mục trong "V. Mẫu chữ" của NĐ30 đều được liệt kê đầy đủ trong báo cáo,
kể cả mục không tự kiểm tra được (đánh dấu "Rà thủ công") — không bỏ sót mục nào.
"""
import argparse
import json
import os
import re
import sys
import html
from datetime import datetime

from docx_format import DocxFormat, twips_to_mm, estimate_text_width_pt

# ----------------------------- chuẩn hóa -----------------------------
def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip())

def squash(s):
    return re.sub(r"\s+", "", (s or "")).upper()

def is_upper_vn(s):
    """Văn bản 'in hoa': có chữ cái và bằng chính nó khi .upper()."""
    s = re.sub(r"[^A-Za-zÀ-ỹ]", "", s)
    return len(s) > 0 and s == s.upper()

# ----------------------------- loại văn bản -----------------------------
TEN_LOAI = {
    "NGHỊ QUYẾT", "QUYẾT ĐỊNH", "CHỈ THỊ", "QUY CHẾ", "QUY ĐỊNH", "THÔNG CÁO",
    "THÔNG BÁO", "HƯỚNG DẪN", "CHƯƠNG TRÌNH", "KẾ HOẠCH", "PHƯƠNG ÁN", "ĐỀ ÁN",
    "DỰ ÁN", "BÁO CÁO", "BIÊN BẢN", "TỜ TRÌNH", "HỢP ĐỒNG", "CÔNG ĐIỆN",
    "BẢN GHI NHỚ", "BẢN THỎA THUẬN", "GIẤY ỦY QUYỀN", "GIẤY MỜI",
    "GIẤY GIỚI THIỆU", "GIẤY NGHỈ PHÉP", "PHIẾU GỬI", "PHIẾU CHUYỂN",
    "PHIẾU BÁO", "PHIẾU TRÌNH",
}

# ----------------------------- so khớp định dạng -----------------------------
TNR_OK = {"times new roman"}

def check_element(run, spec, para=None):
    """So một run đại diện với spec; trả (status, [lỗi])."""
    errs = []
    if run is None:
        return "khong_tim_thay", []

    # cỡ chữ
    cc = spec.get("co_chu")
    if cc and run.size is not None:
        if not (cc["min"] - 0.01 <= run.size <= cc["max"] + 0.01):
            yc = f'{cc["min"]}' if cc["min"] == cc["max"] else f'{cc["min"]}–{cc["max"]}'
            errs.append(f'Cỡ chữ {run.size:g}pt (yêu cầu {yc}pt)')
    elif cc and run.size is None:
        errs.append("Không xác định được cỡ chữ")

    # loại chữ (in hoa / in thường)
    lc = spec.get("loai_chu")
    if lc == "in_hoa":
        disp = run.display
        if not is_upper_vn(disp):
            errs.append("Phải IN HOA")
    # (in_thuong: không bắt buộc thường hoàn toàn vì có thể có chữ hoa đầu)

    # dáng chữ đứng / nghiêng
    dg = spec.get("dang")
    if dg == "nghieng" and not run.italic:
        errs.append("Phải in nghiêng")
    if dg == "dung" and run.italic:
        errs.append("Phải đứng (không nghiêng)")

    # đậm
    dam = spec.get("dam")
    if dam is True and not run.bold:
        errs.append("Phải in đậm")
    if dam is False and run.bold:
        errs.append("Không được in đậm")

    # canh lề (nếu spec yêu cầu và biết alignment)
    cl = spec.get("can_le")
    if cl and para is not None and para.align is not None:
        amap = {"center": "center", "right": "right", "both": "both", "left": "left"}
        if amap.get(para.align) != cl:
            label = {"center": "canh giữa", "right": "canh phải",
                     "both": "canh đều", "left": "canh trái"}[cl]
            errs.append(f"Phải {label}")

    return ("loi" if errs else "dat"), errs

def check_font_color(run, name="phần tử"):
    errs = []
    if run is None:
        return errs
    if run.font and run.font.strip().lower() not in TNR_OK:
        errs.append(f'{name}: phông "{run.font}" (yêu cầu Times New Roman)')
    if run.color and run.color.lower() not in ("000000", "auto", "010000"):
        errs.append(f'{name}: màu chữ #{run.color} (yêu cầu màu đen)')
    return errs

# ----------------------------- phát hiện phần tử -----------------------------
class Detector:
    def __init__(self, doc):
        self.doc = doc
        self.P = doc.paragraphs
        self.n = len(self.P)
        self.found = {}     # key -> (para, run) hoặc (para, run, [extra runs])
        self._detect_all()

    def _set(self, key, para):
        if para is not None and key not in self.found:
            self.found[key] = para

    def _idx_so(self):
        for i, p in enumerate(self.P):
            if re.match(r"^\s*Số\s*:", p.text):
                return i
        return None

    def _detect_all(self):
        P = self.P
        idx_so = self._idx_so()
        idx_kinhgui = None
        idx_noinhan = None

        for i, p in enumerate(P):
            t = norm(p.text)
            if not t:
                continue
            up = squash(t)

            # Quốc hiệu
            if up == squash("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"):
                self._set("quoc_hieu", p)
            # Tiêu ngữ
            if up.replace("–", "-") in (squash("Độc lập - Tự do - Hạnh phúc"),
                                        squash("Độc lập-Tự do-Hạnh phúc")):
                self._set("tieu_ngu", p)
            # Số, ký hiệu
            if re.match(r"^\s*Số\s*:", p.text) and "/" in t:
                self._set("so_ky_hieu", p)
            # Địa danh + thời gian
            if re.search(r"ngày\s+\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4}", t) and "," in t:
                self._set("dia_danh_thoi_gian", p)
            # Trích yếu công văn
            if re.match(r"^\s*V/v", p.text):
                self._set("trich_yeu_cong_van", p)
            # Kính gửi
            if re.match(r"^\s*Kính\s+gửi\s*:", p.text):
                self._set("kinh_gui", p)
                idx_kinhgui = i
            # Nơi nhận:
            if up.rstrip(":") == squash("Nơi nhận") and t.endswith(":"):
                self._set("noi_nhan_tu", p)
                idx_noinhan = i
            # Quyền hạn người ký
            if re.match(r"^\s*(TM\.|KT\.|Q\.|TL\.|TUQ\.)\s", p.text):
                self._set("quyen_han_nguoi_ky", p)
            # Mục số La Mã trong báo cáo (I. ...)
            if re.match(r"^\s*[IVX]+\.\s+\S", t) and is_upper_vn(t):
                self._set("muc_so_bao_cao", p)
            # Điều
            if re.match(r"^\s*Điều\s+\d+\s*\.", p.text):
                self._set("dieu", p)
            # Phần / Chương
            if re.match(r"^\s*(Phần|Chương)\s+[IVX0-9]", p.text):
                self._set("phan_chuong_tu", p)
                # tiêu đề: dòng kế tiếp in hoa
                for j in range(i + 1, min(i + 3, self.n)):
                    if norm(P[j].text) and is_upper_vn(norm(P[j].text)):
                        self._set("phan_chuong_tieu_de", P[j])
                        break
            # Phụ lục
            if re.match(r"^\s*Phụ lục\s+[IVX0-9]", p.text):
                self._set("phu_luc_tu", p)
                for j in range(i + 1, min(i + 3, self.n)):
                    if norm(P[j].text) and is_upper_vn(norm(P[j].text)):
                        self._set("phu_luc_tieu_de", P[j])
                        break

        # Tên loại + trích yếu: dòng in hoa, canh giữa, khớp danh mục loại VB,
        # nằm dưới địa danh/số ký hiệu.
        anchor = idx_so if idx_so is not None else 0
        for i in range(anchor, self.n):
            t = norm(P[i].text)
            if not t:
                continue
            up = squash(t)
            base = up
            # bỏ tiền tố quyền hạn nếu lỡ trùng
            if any(base == squash(x) for x in TEN_LOAI) or \
               any(base.startswith(squash(x)) and len(base) - len(squash(x)) <= 2
                   for x in TEN_LOAI):
                self._set("ten_loai", P[i])
                # trích yếu = dòng (không rỗng) ngay sau tên loại,
                # trước "Căn cứ"/"Kính gửi"/nội dung — phát hiện theo vị trí,
                # còn đậm/cỡ để bước kiểm tra đánh giá.
                for j in range(i + 1, min(i + 5, self.n)):
                    tj = norm(P[j].text)
                    if not tj:
                        continue
                    if re.match(r"^\s*(Căn cứ|Kính gửi|Số:|Điều|V/v)", P[j].text):
                        break
                    self._set("trich_yeu", P[j])
                    break
                break

        # Chữ ký: chức vụ + họ tên (sau quyền hạn, hoặc khối phải/giữa cuối VB)
        self._detect_signature()

        # Đoạn nội dung đại diện
        self._detect_content()

        # Danh sách nơi nhận (gồm dòng "Lưu:")
        if idx_noinhan is not None:
            extra = []
            luu = None
            for j in range(idx_noinhan + 1, self.n):
                tj = norm(P[j].text)
                if not tj:
                    if extra:
                        break
                    continue
                if re.match(r"^\s*-", P[j].text) or re.match(r"^\s*Lưu\s*:", P[j].text):
                    extra.append(P[j])
                    if re.match(r"^\s*[-\s]*Lưu\s*:", P[j].text):
                        luu = P[j]
                        break
                else:
                    break
            if extra:
                self.found["noi_nhan_ds"] = luu or extra[0]
                self.noi_nhan_block = extra
            else:
                self.noi_nhan_block = []
        else:
            self.noi_nhan_block = []

        # Tên cơ quan (chủ quản + ban hành): khối in hoa trên cùng bên trái,
        # KHÁC quốc hiệu/tiêu ngữ, nằm trước (hoặc ngang) số ký hiệu.
        self._detect_org()

    def _detect_signature(self):
        """Nhận diện khối chữ ký từ DƯỚI lên: họ tên -> chức vụ -> quyền hạn."""
        P = self.P
        n = self.n
        start = int(n * 0.45)
        name_idx = None
        for j in range(n - 1, start - 1, -1):
            t = norm(P[j].text)
            if not t:
                continue
            if re.match(r"^\s*(-|Lưu|Nơi nhận|Kính gửi|Số\s*:)", t):
                continue
            if re.match(r"^[IVX]+\.", t) or re.match(r"^Điều\s", t):
                continue
            if t.endswith((";", ".", ":", ",")):
                continue
            words = t.split()
            if not (2 <= len(words) <= 6):
                continue
            if is_upper_vn(t):
                continue
            # họ tên: mỗi từ viết hoa chữ đầu; ưu tiên đậm hoặc canh phải/giữa
            if not all(w[:1] == w[:1].upper() for w in words if w[:1].isalpha()):
                continue
            dr = P[j].dominant_run()
            strong = (dr is not None and dr.bold) or P[j].align in ("right", "center")
            if strong:
                name_idx = j
                break
        if name_idx is None:
            return
        self._set("ho_ten_nguoi_ky", P[name_idx])
        # chức vụ/quyền hạn: trong tối đa 3 dòng không rỗng phía trên tên
        cnt = 0
        for i in range(name_idx - 1, -1, -1):
            t = norm(P[i].text)
            if not t:
                continue
            cnt += 1
            if re.match(r"^\s*(TM\.|KT\.|Q\.|TL\.|TUQ\.)", P[i].text):
                self._set("quyen_han_nguoi_ky", P[i])
            elif is_upper_vn(t) and not re.match(r"^[IVX]+\.", t) \
                    and "chuc_vu_nguoi_ky" not in self.found:
                self._set("chuc_vu_nguoi_ky", P[i])
            if cnt >= 3:
                break

    def _detect_content(self):
        """Đoạn nội dung đại diện: đoạn dài nhất chưa gán, không phải căn cứ/heading."""
        used = set(id(p) for p in self.found.values())
        best, blen = None, 0
        for p in self.P:
            if id(p) in used:
                continue
            t = norm(p.text)
            if len(t) < 40:
                continue
            if re.match(r"^\s*(Căn cứ|Kính gửi|Số\s*:|Điều\s|[IVX]+\.|Phần|Chương|Phụ lục)", p.text):
                continue
            if is_upper_vn(t):
                continue
            if len(t) > blen:
                best, blen = p, len(t)
        self._set("noi_dung", best)

    def _detect_org(self):
        P = self.P
        idx_so = self._idx_so()
        qh = self.found.get("quoc_hieu")
        limit = P.index(qh) if (qh in P) else (idx_so if idx_so else 8)
        limit = max(limit, idx_so or 0) + 2
        cand = []
        for i in range(0, min(limit, self.n)):
            p = P[i]
            t = norm(p.text)
            if not t:
                continue
            if p is self.found.get("quoc_hieu") or p is self.found.get("tieu_ngu"):
                continue
            if re.match(r"^\s*Số\s*:", p.text):
                continue
            if is_upper_vn(t) and len(t) <= 80:
                cand.append(p)
        if not cand:
            return
        # ban hành = dòng in hoa ĐẬM cuối cùng; chủ quản = dòng in hoa không đậm phía trên
        banhanh = None
        for p in cand:
            dr = p.dominant_run()
            if dr is not None and dr.bold:
                banhanh = p
        if banhanh is None:
            banhanh = cand[-1]
        self._set("ten_cq_ban_hanh", banhanh)
        # chủ quản: dòng in hoa NGAY TRÊN ban hành mà không đậm
        bidx = P.index(banhanh)
        for i in range(bidx - 1, -1, -1):
            p = P[i]
            t = norm(p.text)
            if not t:
                continue
            if p in (self.found.get("quoc_hieu"), self.found.get("tieu_ngu")):
                continue
            if is_upper_vn(t):
                dr = p.dominant_run()
                if dr is not None and not dr.bold:
                    self._set("ten_cq_chu_quan", p)
                break


# ----------------------------- chạy kiểm tra -----------------------------
def check_duong_ke(doc, det, item, r):
    """Kiểm đường kẻ ngang (shape, nét 0,75pt, độ dài theo tỉ lệ) dưới một dòng chữ.
    Ghi kết quả vào dict r (đã khởi tạo sẵn các trường)."""
    anchor = det.found.get(item.get("duoi"))
    if anchor is None or anchor.index is None:
        r["status"] = "khong_tim_thay"
        r["thuc_te"] = "không xác định được dòng chữ phía trên để soi đường kẻ"
        return
    shapes, border = doc.lines_near(anchor.index, lookahead=2)
    run = anchor.dominant_run()
    size = run.size if (run and run.size) else 13.0
    tw = estimate_text_width_pt(anchor.text, size)
    errs, warns = [], []

    if not shapes and not border:
        r["status"] = "loi"
        r["loi"] = [f'Không thấy đường kẻ ngang dưới "{anchor.text.strip()[:40]}"']
        r["thuc_te"] = "không có đường kẻ"
        return
    if not shapes and border:
        r["status"] = "loi"
        bs = border.get("sz_pt")
        r["loi"] = [f'Đường kẻ đang là BORDER đáy đoạn (nét {bs}pt) — quy ước yêu cầu dạng SHAPE '
                    f'(đường kẻ vẽ riêng) để chỉnh đúng độ dài & canh giữa. Cần vẽ lại bằng shape.']
        r["thuc_te"] = f"border đáy đoạn, nét {bs}pt"
        return

    ln = max(shapes, key=lambda s: (s["length_pt"] or 0))
    w, L = ln["weight_pt"], ln["length_pt"]
    parts = [f'shape ({ln["kind"]})']
    # nét
    if w is None:
        warns.append("không đọc được độ rộng nét — kiểm thủ công (yêu cầu 0,75pt)")
        parts.append("nét: ?")
    else:
        parts.append(f"nét {w}pt")
        if abs(w - 0.75) > 0.06:
            errs.append(f"Độ rộng nét {w}pt — yêu cầu 0,75pt")
    # độ dài
    if L and tw:
        ratio = L / tw
        parts.append(f"dài ≈{L:.0f}pt (chữ ≈{tw:.0f}pt, tỉ lệ {ratio:.2f})")
        lo, hi = item.get("ti_le_min", 0), item.get("ti_le_max", 99)
        if not (lo <= ratio <= hi):
            warns.append(f"Độ dài lệch: tỉ lệ {ratio:.2f}, yêu cầu {lo:.2f}–{hi:.2f} "
                         f"({item.get('do_dai','')}) — ước lượng, kiểm lại bằng mắt")
    elif L:
        parts.append(f"dài ≈{L:.0f}pt")
        warns.append("chưa ước lượng được bề rộng chữ để so tỉ lệ — kiểm thủ công")
    else:
        warns.append("không đo được độ dài đường kẻ — kiểm thủ công")
    r["thuc_te"] = ", ".join(parts)
    if errs:
        r["status"] = "loi"
    elif warns:
        r["status"] = "canh_bao"
    else:
        r["status"] = "dat"
    r["loi"] = errs + warns


def run_checks(doc, spec):
    det = Detector(doc)
    results = {"quy_dinh_chung": [], "mau_chu": [],
               "font_mau": [], "tom_tat": {}}

    # ---- Quy định chung ----
    ps = doc.page_setup()
    # khổ giấy A4
    for item in spec["quy_dinh_chung"]:
        r = {"key": item["key"], "ten": item["ten"], "can": item["can"],
             "status": "thu_cong", "loi": [], "thuc_te": ""}
        kt = item.get("kiem_tra")
        if kt == "kho_giay":
            w, h = ps["w"], ps["h"]
            r["thuc_te"] = f'{twips_to_mm(w)}×{twips_to_mm(h)} mm' if w else "—"
            if w and h:
                okw = abs(w - 11906) <= 80
                okh = abs(h - 16838) <= 80
                r["status"] = "dat" if (okw and okh) else "loi"
                if not (okw and okh):
                    r["loi"].append("Khổ giấy không phải A4 (210×297mm)")
            else:
                r["status"] = "khong_tim_thay"
        elif kt == "huong_giay":
            r["thuc_te"] = ps.get("orient") or "—"
            if ps.get("orient") == "landscape":
                r["status"] = "loi"
                r["loi"].append("Trang đang nằm ngang (landscape); mặc định phải dọc")
            elif ps.get("orient"):
                r["status"] = "dat"
        elif kt == "le_trang":
            t, b, l, rr = (twips_to_mm(ps["top"]), twips_to_mm(ps["bottom"]),
                           twips_to_mm(ps["left"]), twips_to_mm(ps["right"]))
            r["thuc_te"] = f"trên {t}, dưới {b}, trái {l}, phải {rr} (mm)"
            def within(v, lo, hi, name):
                if v is None:
                    return f"thiếu lề {name}"
                if not (lo - 0.6 <= v <= hi + 0.6):
                    return f"lề {name} {v}mm (yêu cầu {lo}–{hi}mm)"
                return None
            for msg in (within(t, 20, 25, "trên"), within(b, 20, 25, "dưới"),
                        within(l, 30, 35, "trái"), within(rr, 15, 20, "phải")):
                if msg:
                    r["loi"].append(msg)
            r["status"] = "loi" if r["loi"] else "dat"
        elif kt == "phong_chu":
            # lấy font đa số trong nội dung
            fonts = {}
            for p in doc.paragraphs:
                for rn in p.runs:
                    if rn.text.strip() and rn.font:
                        fonts[rn.font] = fonts.get(rn.font, 0) + len(rn.text.strip())
            if fonts:
                main = max(fonts, key=fonts.get)
                r["thuc_te"] = main
                bad = [f for f in fonts if f.strip().lower() not in TNR_OK]
                if main.strip().lower() in TNR_OK and not bad:
                    r["status"] = "dat"
                elif main.strip().lower() in TNR_OK and bad:
                    r["status"] = "loi"
                    r["loi"].append("Có phông khác Times New Roman: " + ", ".join(sorted(set(bad))[:5]))
                else:
                    r["status"] = "loi"
                    r["loi"].append(f'Phông chính "{main}" không phải Times New Roman')
            else:
                r["thuc_te"] = "(thừa kế mặc định)"
                r["status"] = "thu_cong"
        elif kt == "dau_gach":
            EN, EM = "\u2013", "\u2014"
            hits = []
            tieu_ngu_hit = False
            for p in doc.paragraphs:
                txt = p.text
                if EN in txt or EM in txt:
                    ctx = txt.strip()
                    if len(ctx) > 60:
                        ctx = ctx[:57] + "…"
                    hits.append(ctx)
                    if det.found.get("tieu_ngu") is not None and p is det.found["tieu_ngu"]:
                        tieu_ngu_hit = True
            n = len(hits)
            if n == 0:
                r["status"] = "dat"
                r["thuc_te"] = 'dùng gạch nối thường "-"'
            else:
                r["status"] = "loi"
                r["thuc_te"] = f'{n} dòng dùng gạch dài "–"/"—"'
                if tieu_ngu_hit:
                    r["loi"].append('Tiêu ngữ đang dùng gạch dài — phải là "Độc lập - Tự do - Hạnh phúc" (gạch nối thường "-")')
                for h in hits[:6]:
                    r["loi"].append(f'Gạch dài tại: "{h}"')
                if n > 6:
                    r["loi"].append(f"… và {n-6} dòng khác")
        results["quy_dinh_chung"].append(r)

    # số trang (đưa vào quy định chung phần kiểm tra)
    sotrang = {"key": "so_trang_general", "ten": "Số trang (đánh số tự động ở lề trên/dưới)",
               "can": "Phần I, Mục I.7", "status": "thu_cong", "loi": [], "thuc_te": ""}
    sotrang["thuc_te"] = "có trường số trang" if doc.has_page_number() else "không thấy trường số trang tự động"
    sotrang["status"] = "dat" if doc.has_page_number() else "canh_bao"
    if not doc.has_page_number():
        sotrang["loi"].append("Không phát hiện đánh số trang tự động — kiểm tra thủ công")
    results["quy_dinh_chung"].append(sotrang)

    # ---- Mẫu chữ (Mục V) — liệt kê TẤT CẢ ----
    for item in spec["mau_chu"]:
        r = {"key": item["key"], "stt": item.get("stt", ""), "ten": item["ten"],
             "o_so": item.get("o_so", ""), "yeu_cau": fmt_requirement(item),
             "vi_du": item.get("vi_du", ""), "ghi_chu": item.get("ghi_chu", ""),
             "auto": item.get("auto", False),
             "status": "thu_cong", "loi": [], "thuc_te": ""}
        if not item.get("auto", False):
            r["status"] = "thu_cong"
            results["mau_chu"].append(r)
            continue

        if item.get("kiem_tra") == "duong_ke":
            check_duong_ke(doc, det, item, r)
            results["mau_chu"].append(r)
            continue

        para = det.found.get(item["key"])
        if para is None:
            r["status"] = "khong_tim_thay"
            results["mau_chu"].append(r)
            continue

        # chọn run đại diện
        run = pick_run(item["key"], para)
        r["thuc_te"] = describe_run(run, para)
        st, errs = check_element(run, item, para)
        # font/màu cho run này
        errs += check_font_color(run, "")
        r["loi"] = [e for e in errs if e]
        r["status"] = "loi" if r["loi"] else "dat"
        results["mau_chu"].append(r)

    # ---- tóm tắt ----
    all_items = results["quy_dinh_chung"] + results["mau_chu"]
    cnt = {"dat": 0, "loi": 0, "khong_tim_thay": 0, "thu_cong": 0, "canh_bao": 0}
    for it in all_items:
        cnt[it["status"]] = cnt.get(it["status"], 0) + 1
    results["tom_tat"] = cnt
    results["_detected_keys"] = sorted(det.found.keys())
    return results, det


def pick_run(key, para):
    """Run đại diện cho từng phần tử (ví dụ 'Số' lấy run đầu, ký hiệu lấy sau '/')."""
    if key == "so_ky_hieu":
        # ưu tiên run chứa chữ "Số"
        for r in para.runs:
            if "Số" in r.text:
                return r
    return para.dominant_run()


def describe_run(run, para):
    if run is None:
        return "—"
    parts = []
    parts.append(run.font or "?font")
    parts.append(f"{run.size:g}pt" if run.size is not None else "?pt")
    sty = []
    sty.append("đậm" if run.bold else "thường")
    sty.append("nghiêng" if run.italic else "đứng")
    if run.caps or is_upper_vn(run.display):
        sty.append("IN HOA")
    parts.append("/".join(sty))
    if para is not None and para.align:
        amap = {"center": "giữa", "right": "phải", "both": "đều", "left": "trái"}
        parts.append("canh " + amap.get(para.align, para.align))
    return " · ".join(parts)


def fmt_requirement(item):
    if item.get("kiem_tra") == "duong_ke":
        bits = ["Đường kẻ dạng shape", "nét 0,75pt"]
        if item.get("do_dai"):
            bits.append(item["do_dai"])
        if item.get("canh") == "giữa":
            bits.append("canh giữa")
        return "; ".join(bits)
    if item.get("kiem_tra") == "dau_gach":
        return 'Gạch nối thường "-"'
    p = []
    lc = item.get("loai_chu")
    if lc == "in_hoa":
        p.append("In hoa")
    elif lc == "in_thuong":
        p.append("In thường")
    cc = item.get("co_chu")
    if cc:
        p.append(f'{cc["min"]}pt' if cc["min"] == cc["max"] else f'{cc["min"]}–{cc["max"]}pt')
    dg = item.get("dang")
    dam = item.get("dam")
    style = []
    if dg == "dung":
        style.append("đứng")
    elif dg == "nghieng":
        style.append("nghiêng")
    if dam is True:
        style.append("đậm")
    if style:
        p.append(", ".join(style))
    cl = item.get("can_le")
    if cl:
        p.append({"center": "canh giữa", "right": "canh phải",
                  "both": "canh đều", "left": "canh trái"}[cl])
    return "; ".join(p) if p else "—"


# ----------------------------- báo cáo HTML -----------------------------
STATUS_LABEL = {
    "dat": ("ĐẠT", "#15803d", "#dcfce7"),
    "loi": ("LỖI", "#b91c1c", "#fee2e2"),
    "khong_tim_thay": ("KHÔNG THẤY", "#92400e", "#fef3c7"),
    "thu_cong": ("RÀ THỦ CÔNG", "#1e40af", "#dbeafe"),
    "canh_bao": ("CẢNH BÁO", "#92400e", "#fef3c7"),
}

def badge(status):
    label, fg, bg = STATUS_LABEL.get(status, (status, "#374151", "#f3f4f6"))
    return f'<span class="badge" style="color:{fg};background:{bg}">{label}</span>'

def esc(s):
    return html.escape(str(s or ""))

def render_rows(items, mau=False):
    rows = []
    for it in items:
        loi = "<br>".join("• " + esc(e) for e in it.get("loi", [])) or "—"
        if mau:
            rows.append(f"""<tr class="r-{it['status']}">
  <td class="c-stt">{esc(it.get('stt',''))}</td>
  <td class="c-ten"><b>{esc(it['ten'])}</b>{(' <span class=oso>(ô '+esc(it['o_so'])+')</span>') if it.get('o_so') and it['o_so']!='-' else ''}
      {('<div class=vd>VD: '+esc(it['vi_du'])+'</div>') if it.get('vi_du') else ''}</td>
  <td class="c-yc">{esc(it.get('yeu_cau',''))}</td>
  <td class="c-tt">{esc(it.get('thuc_te','') or '—')}</td>
  <td class="c-bd">{badge(it['status'])}</td>
  <td class="c-loi">{loi}{('<div class=gc>'+esc(it['ghi_chu'])+'</div>') if it.get('ghi_chu') else ''}</td>
</tr>""")
        else:
            rows.append(f"""<tr class="r-{it['status']}">
  <td class="c-ten"><b>{esc(it['ten'])}</b><div class=oso>{esc(it.get('can',''))}</div></td>
  <td class="c-tt">{esc(it.get('thuc_te','') or '—')}</td>
  <td class="c-bd">{badge(it['status'])}</td>
  <td class="c-loi">{loi}</td>
</tr>""")
    return "\n".join(rows)

def build_html(results, doc_name):
    s = results["tom_tat"]
    total = sum(s.values())
    chung = render_rows(results["quy_dinh_chung"], mau=False)
    mau = render_rows(results["mau_chu"], mau=True)
    now = datetime.now().strftime("%H:%M %d/%m/%Y")
    return f"""<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Báo cáo rà soát thể thức — {esc(doc_name)}</title>
<style>
 *{{box-sizing:border-box}}
 body{{font-family:'Segoe UI',Arial,sans-serif;margin:0;background:#f8fafc;color:#0f172a;line-height:1.5}}
 .wrap{{max-width:1080px;margin:0 auto;padding:24px}}
 h1{{font-size:20px;margin:0 0 4px}}
 .sub{{color:#64748b;font-size:13px;margin-bottom:18px}}
 .cards{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:22px}}
 .card{{flex:1;min-width:120px;border-radius:10px;padding:12px 14px;border:1px solid #e2e8f0;background:#fff}}
 .card .num{{font-size:26px;font-weight:700;line-height:1}}
 .card .lbl{{font-size:12px;color:#64748b;margin-top:4px}}
 h2{{font-size:15px;margin:26px 0 8px;padding-bottom:6px;border-bottom:2px solid #e2e8f0}}
 table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;font-size:13px}}
 th{{background:#f1f5f9;text-align:left;padding:8px 10px;font-size:12px;color:#334155;border-bottom:1px solid #e2e8f0}}
 td{{padding:8px 10px;border-bottom:1px solid #f1f5f9;vertical-align:top}}
 tr:last-child td{{border-bottom:none}}
 .badge{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;white-space:nowrap}}
 .oso{{color:#94a3b8;font-size:11px;font-weight:400}}
 .vd{{color:#64748b;font-size:11px;margin-top:2px;font-style:italic}}
 .gc{{color:#1e40af;font-size:11px;margin-top:3px}}
 .c-stt{{width:34px;color:#94a3b8;font-weight:700}}
 .c-bd{{width:96px}} .c-yc{{width:170px;color:#475569}} .c-tt{{width:200px;color:#0f172a}}
 .r-loi{{background:#fff7f7}} .r-khong_tim_thay{{background:#fffdf5}}
 .note{{font-size:12px;color:#64748b;margin-top:18px;padding:12px;background:#fff;border:1px solid #e2e8f0;border-radius:8px}}
 .legend span{{margin-right:12px}}
</style></head>
<body><div class="wrap">
 <h1>Báo cáo rà soát thể thức văn bản hành chính</h1>
 <div class="sub">Văn bản: <b>{esc(doc_name)}</b> · Đối chiếu Phụ lục I Nghị định 30/2020/NĐ-CP · Lập lúc {now}</div>
 <div class="cards">
   <div class="card"><div class="num" style="color:#15803d">{s.get('dat',0)}</div><div class="lbl">Đạt</div></div>
   <div class="card"><div class="num" style="color:#b91c1c">{s.get('loi',0)}</div><div class="lbl">Lỗi</div></div>
   <div class="card"><div class="num" style="color:#92400e">{s.get('khong_tim_thay',0)+s.get('canh_bao',0)}</div><div class="lbl">Không thấy / Cảnh báo</div></div>
   <div class="card"><div class="num" style="color:#1e40af">{s.get('thu_cong',0)}</div><div class="lbl">Rà thủ công</div></div>
   <div class="card"><div class="num">{total}</div><div class="lbl">Tổng mục</div></div>
 </div>

 <h2>A. Quy định chung (Mục I) &amp; số trang</h2>
 <table><thead><tr><th>Thành phần</th><th>Thực tế</th><th>Kết quả</th><th>Ghi chú / Lỗi</th></tr></thead>
 <tbody>{chung}</tbody></table>

 <h2>B. Mẫu chữ &amp; chi tiết trình bày (Mục V) — đầy đủ {len(results['mau_chu'])} mục</h2>
 <table><thead><tr><th>STT</th><th>Thành phần thể thức</th><th>Yêu cầu</th><th>Thực tế (run đại diện)</th><th>Kết quả</th><th>Ghi chú / Lỗi</th></tr></thead>
 <tbody>{mau}</tbody></table>

 <div class="note">
  <div class="legend"><b>Chú giải:</b>
   <span>{badge('dat')} đúng quy định</span>
   <span>{badge('loi')} sai cần sửa</span>
   <span>{badge('khong_tim_thay')} không phát hiện trong văn bản</span>
   <span>{badge('thu_cong')} công cụ không tự kiểm tra, cần người rà</span>
  </div>
  <p style="margin:8px 0 0">Báo cáo liệt kê <b>đầy đủ mọi mục trong Mục V “Mẫu chữ và chi tiết trình bày”</b> của Nghị định 30/2020/NĐ-CP, kể cả mục chỉ rà thủ công (dòng kẻ, dấu khẩn/mật, chỉ dẫn lưu hành, địa chỉ cơ quan…). “KHÔNG THẤY” nghĩa là phần tử không bắt buộc có ở loại văn bản này hoặc công cụ chưa nhận diện được — nên đối chiếu lại bằng mắt.</p>
 </div>
</div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docx")
    ap.add_argument("--out", default="ket_qua_thethuc")
    ap.add_argument("--spec", default=os.path.join(
        os.path.dirname(__file__), "..", "reference", "nd30_spec.json"))
    args = ap.parse_args()

    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)

    doc = DocxFormat(args.docx)
    results, det = run_checks(doc, spec)

    os.makedirs(args.out, exist_ok=True)
    doc_name = os.path.basename(args.docx)
    with open(os.path.join(args.out, "ket_qua.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out, "bao_cao.html"), "w", encoding="utf-8") as f:
        f.write(build_html(results, doc_name))

    s = results["tom_tat"]
    print(f"Đạt {s.get('dat',0)} · Lỗi {s.get('loi',0)} · "
          f"Không thấy {s.get('khong_tim_thay',0)} · Rà thủ công {s.get('thu_cong',0)}")
    print("Phần tử phát hiện được:", ", ".join(results["_detected_keys"]))
    print("→", os.path.join(args.out, "bao_cao.html"))


if __name__ == "__main__":
    main()
