---
name: kiem-tra-the-thuc-van-ban
description: Kiểm tra & tự sửa thể thức văn bản hành chính (phông, cỡ, kiểu chữ, canh lề, khổ giấy) theo Phụ lục I Nghị định 30/2020/NĐ-CP, rà đủ Mục V; xuất báo cáo HTML mã màu và .docx đã sửa.
dependencies: lxml
---

# Kiểm tra & sửa thể thức văn bản hành chính theo Nghị định 30/2020/NĐ-CP

## Khi nào dùng skill này

Khi cần **rà soát cách trình bày (thể thức)** của một văn bản hành chính trước khi phát hành: phông chữ, cỡ chữ, kiểu chữ (đứng/nghiêng/đậm), in hoa/in thường, canh lề, khổ giấy, định lề trang, số trang… đối chiếu **Phụ lục I Nghị định 30/2020/NĐ-CP**.

Gọi skill này khi người dùng yêu cầu (kể cả nói ngắn): "kiểm tra thể thức", "rà thể thức văn bản", "check thể thức theo NĐ 30", "kiểm tra văn bản đúng thể thức chưa", "soát cỡ chữ / kiểu chữ / canh lề", "kiểm tra trình bày văn bản hành chính", "báo cáo lỗi thể thức", "sửa thể thức cho đúng NĐ30", hoặc đưa một file `.doc`/`.docx` văn bản hành chính (Tờ trình, Công văn, Báo cáo, Quyết định, Kế hoạch…) và hỏi đã đúng thể thức / quy chuẩn trình bày chưa.

Phân biệt với skill `kiem-tra-chuan-van-ban`: skill kia rà **nội dung chữ** (tên cơ quan, thuật ngữ viết đúng chưa); skill này rà **định dạng/thể thức** (font, cỡ, kiểu chữ, bố cục). KHÔNG dùng skill này cho việc rà tên riêng/thuật ngữ. Có thể chạy cả hai cho một văn bản.

## Nguyên tắc cốt lõi — không bỏ sót mục nào của Mục V

Yêu cầu bắt buộc: báo cáo **liệt kê đầy đủ TẤT CẢ các mục** trong *"Mục V. Mẫu chữ và chi tiết trình bày thể thức văn bản hành chính"* của NĐ30 — kể cả mục công cụ chưa tự kiểm tra được (dòng kẻ, dấu khẩn/mật, chỉ dẫn lưu hành, ký hiệu người soạn, địa chỉ cơ quan). Mỗi mục mang một trạng thái:

| Trạng thái | Ý nghĩa |
|---|---|
| **ĐẠT** | Định dạng đúng quy định |
| **LỖI** | Sai, kèm mô tả lỗi cụ thể (cỡ chữ/kiểu chữ/đậm/canh lề…) |
| **KHÔNG THẤY** | Phần tử không bắt buộc có ở loại VB này, hoặc công cụ chưa nhận diện được → rà lại bằng mắt |
| **RÀ THỦ CÔNG** | Không kiểm tra tự động được (đường kẻ, dấu khẩn, khung viền…) → người soát tự đối chiếu |

Bộ chuẩn (nguồn sự thật) nằm ở `reference/nd30_spec.json`, mã hóa từng dòng của Mục V (loại chữ, cỡ chữ, dáng, đậm, canh lề) cộng các quy định chung ở Mục I (khổ giấy, lề, phông, số trang). Sửa file này nếu cơ quan có quy ước riêng (vd luôn dùng cỡ 13pt).

## Quy trình

1. **Chuẩn bị file.** Nếu là `.doc` (cũ) phải chuyển sang `.docx` trước:
   ```bash
   python /mnt/skills/public/docx/scripts/office/soffice.py --headless --convert-to docx VANBAN.doc
   ```
2. **Chạy kiểm tra** → sinh `bao_cao.html` (mã màu) + `ket_qua.json`:
   ```bash
   python scripts/check_thethuc.py VANBAN.docx --out ket_qua_thethuc
   ```
3. **Đọc báo cáo, trao đổi với người dùng.** Trình bày tóm tắt (bao nhiêu Đạt / Lỗi / Không thấy / Rà thủ công) và liệt kê các LỖI cụ thể. Với mục KHÔNG THẤY ở loại văn bản đang xét, nhắc người dùng kiểm tra lại bằng mắt.
4. **(Tùy chọn) Tự sửa lỗi** → file `.docx` mới:
   ```bash
   python scripts/fix_thethuc.py VANBAN.docx --out VANBAN_daSua.docx
   ```
   Sau khi sửa, **luôn chạy lại** `check_thethuc.py` trên file đã sửa để xác nhận hết lỗi, và validate:
   ```bash
   python /mnt/skills/public/docx/scripts/office/validate.py VANBAN_daSua.docx
   ```
5. **Bàn giao.** Dùng `present_files` đưa `bao_cao.html` (và file đã sửa nếu có).

## Hai điểm LUÔN PHẢI check kỹ (bắt buộc)

**1) Dấu gạch nối.** Dấu nối trong văn bản phải là **gạch nối thường `-` (U+002D)**, KHÔNG dùng gạch dài `–` (en-dash) hay `—` (em-dash). Đặc biệt **Tiêu ngữ** phải là `Độc lập - Tự do - Hạnh phúc` (gạch nối thường, có dấu cách hai bên). Bộ kiểm quét toàn văn bản, báo mọi vị trí dùng gạch dài; bộ sửa thay tất cả `–`/`—` thành `-`.

**2) Đường kẻ ngang dưới Tiêu ngữ và dưới tên cơ quan ban hành.** Phải là **đường kẻ dạng SHAPE** (đường kẻ vẽ riêng — VML `v:line`/`v:rect` hoặc DrawingML), **độ rộng nét 0,75pt**, **canh giữa**, độ dài theo quy định:
- dưới **Tiêu ngữ**: dài **bằng** dòng Tiêu ngữ;
- dưới **tên cơ quan ban hành** (và dưới trích yếu công văn): dài **1/3–1/2** dòng chữ.

Bộ kiểm đọc **chính xác** loại đường kẻ (shape/border) và **độ rộng nét** (so 0,75pt → ĐẠT/LỖI); **độ dài** được đo và đối chiếu tỉ lệ theo **ước lượng** bề rộng chữ (trạng thái CẢNH BÁO kèm số đo, cần liếc mắt xác nhận). Nếu đường kẻ đang là **border đáy đoạn** thay vì shape → báo LỖI (phải vẽ lại bằng shape để chỉnh đúng độ dài & canh giữa). Bộ sửa **ép nét shape về 0,75pt**; KHÔNG tự tạo đường kẻ còn thiếu và KHÔNG đổi độ dài (tránh vỡ layout) — các trường hợp này để chỉnh tay theo gợi ý trong báo cáo.

## Bộ sửa làm gì / KHÔNG làm gì

`fix_thethuc.py` tác động lên **phần tử đã nhận diện và đang báo LỖI (auto)**:
- đặt phông **Times New Roman**, màu **đen**;
- **kẹp cỡ chữ** về đúng khoảng cho phép (vd Số ký hiệu → 13pt; nội dung 13–14pt; "Nơi nhận" → 12pt; danh sách nơi nhận → 11pt);
- đặt **đậm/nghiêng** theo quy định;
- bật **in hoa** (`w:caps`, hiển thị hoa, không phá nội dung gốc) cho phần tử yêu cầu IN HOA mà chưa in hoa;
- thay mọi **gạch dài `–`/`—` → gạch nối `-`** trong toàn văn bản;
- **ép độ rộng nét đường kẻ shape về 0,75pt** (Tiêu ngữ / tên cơ quan / trích yếu).

Bộ sửa **không** tự viết hoa lại nội dung, **không** tạo đường kẻ còn thiếu, **không** đổi độ dài đường kẻ, **không** đụng các mục "rà thủ công", và **giữ nguyên** mọi phần khác của tệp (ảnh, bảng, header/footer, `settings.xml`, quan hệ). Chỉ `word/document.xml` được ghi lại.

> Lưu ý: bộ sửa cố ý **bảo thủ**. Lỗi bố cục (thiếu đường kẻ, sai khoảng cách đoạn, dấu khẩn/mật) không tự sửa — phải chỉnh tay theo gợi ý trong báo cáo.

## Phạm vi tự nhận diện (auto)

Nhận diện theo nội dung + vị trí, hoạt động cả khi tiêu đề nằm trong **bảng 2 cột** (cơ quan trái / Quốc hiệu phải):
Quốc hiệu, Tiêu ngữ, tên cơ quan chủ quản & ban hành, Số–ký hiệu, địa danh–thời gian, tên loại + trích yếu, trích yếu công văn (V/v), Kính gửi, nội dung, mục La Mã (I., II.), Điều, Phần/Chương + tiêu đề, Phụ lục + tiêu đề, quyền hạn/chức vụ/họ tên người ký, "Nơi nhận" + danh sách (gồm dòng "Lưu:").
**Dấu gạch nối** (toàn văn bản) và **đường kẻ ngang dạng shape** dưới Tiêu ngữ / tên cơ quan / trích yếu (nét 0,75pt + độ dài) → kiểm tự động (xem mục "Hai điểm LUÔN PHẢI check kỹ").
Khổ giấy A4, định lề, phông chữ chính, hướng giấy, số trang tự động → kiểm ở phần "Quy định chung".

Các mục **rà thủ công** (vẫn liệt kê trong báo cáo): tiêu đề Mục/Tiểu mục; khoản, điểm; dấu mức độ khẩn; ký hiệu người soạn thảo & số lượng bản; địa chỉ cơ quan/email/website; chỉ dẫn phạm vi lưu hành.

## Cấu trúc thư mục skill

```
kiem-tra-the-thuc-van-ban/
  SKILL.md
  reference/
    nd30_spec.json        # bộ chuẩn Mục I + Mục V (sửa khi có quy ước riêng)
  scripts/
    docx_format.py        # đọc .docx, phân giải định dạng hiệu lực của từng run
    check_thethuc.py      # phát hiện + đối chiếu + xuất báo cáo HTML
    fix_thethuc.py        # tự sửa lỗi → .docx mới
```

## Lưu ý bắt buộc

- **Không khẳng định tuyệt đối.** Công cụ phát hiện theo heuristic; luôn nhắc người dùng đối chiếu lại các mục "KHÔNG THẤY"/"RÀ THỦ CÔNG" và rà với cán bộ văn thư trước khi phát hành.
- **Khoảng cỡ chữ là chuẩn.** NĐ30 cho nhiều thành phần một *khoảng* (vd 13–14pt). Báo cáo coi đúng khi nằm trong khoảng; cần đồng bộ một cỡ trong toàn văn bản thì chỉnh `nd30_spec.json` về cỡ cố định.
- **Phần tử trong bảng** vẫn được quét (script duyệt mọi `<w:p>`, kể cả trong ô bảng).
- Cỡ chữ đọc theo `w:sz` (nửa-point). Đậm/nghiêng/in hoa được phân giải qua chuỗi kế thừa style → docDefaults, nên vẫn đúng khi định dạng đặt ở cấp style chứ không ở run.
