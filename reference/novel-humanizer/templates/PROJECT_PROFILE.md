# PROJECT PROFILE — v3.0 | MẪU ĐIỀN CHO MỖI TRUYỆN

> Sao chép file này thành `PROJECT_PROFILE.md` cho **từng dự án**. Xóa những ô không dùng; không cần điền hết trước khi bắt đầu viết. `CHƯA CHỐT` là một trạng thái hợp lệ.

## A. Thông tin nền

- **PROJECT_ID:** ...
- **Tên truyện:** ...
- **Thể loại/chất liệu pha trộn:** ...
- **Đối tượng độc giả/nền tảng:** ...
- **Ý tưởng trung tâm và lời hứa với độc giả:** ...
- **Trạng thái:** thử nghiệm / đang viết / đang biên tập / canon đã khóa

## B. STYLE_PROFILE

| Thuộc tính | Giá trị tác giả chọn | Mức ràng buộc | Phạm vi |
|---|---|---|---|
| Giọng người kể | ... | HARD / PREFERRED / AVOID / OPEN | project/arc/chapter/scene |
| Ngôi kể, điểm nhìn | ... | ... | ... |
| Nhịp tổng thể và biến thiên | ... | ... | ... |
| Cấu trúc câu/đoạn và ngắt dòng | ... | ... | ... |
| Từ vựng, mức khẩu ngữ/Hán Việt | ... | ... | ... |
| Đối thoại | ... | ... | ... |
| Tỷ lệ hành động/miêu tả/nội tâm | ... | ... | ... |
| Ẩn dụ, biểu tượng, điệp cấu trúc | ... | ... | ... |
| Mức hài, cảm xúc, tối/tươi | ... | ... | ... |
| Nhịp mở/kết cảnh và cliffhanger | ... | ... | ... |
| Định dạng xuất bản | ... | ... | ... |

**Mẫu chuẩn đã duyệt:** [đường dẫn hoặc trích đoạn]

**Chống mẫu (tác giả không muốn):** [đường dẫn hoặc trích đoạn]

**Phân biệt lời kể và lời từng nhân vật:**

- Nhân vật A: từ ngữ/nhịp nói/điều hay giấu: ...
- Nhân vật B: ...

**Ngoại lệ theo cảnh:** ...

## C. Quy tắc can thiệp của AI

- **Được tự sửa:** [chính tả, liên từ, trùng ý, lỗi continuity chắc chắn...]
- **Chỉ được góp ý, chờ duyệt:** [đổi cốt truyện, thay số phận nhân vật, thêm lore, đảo POV...]
- **DO_NOT_TOUCH:** [đoạn, nhân vật, câu thoại, chương đã khóa...]
- **Mức tự do khi viết mới:** thấp / trung bình / cao, kèm ranh giới: ...
- **Độ dài chương mục tiêu:** ... (không bắt buộc, có thể thay theo chương)
- **Định dạng kết quả:** văn truyện / QC / patch / diff / JSON / tệp Markdown ...

## D. STORY_BIBLE & CANON

### CANON_LOCKED — chỉ tác giả duyệt sửa

| Chủ đề | Dữ kiện đã chốt | Nguồn/chương chốt |
|---|---|---|
| Thế giới và địa lý | ... | ... |
| Hệ thống phép thuật/công nghệ/tu luyện | ... | ... |
| Nhân vật | ... | ... |
| Lịch sử và niên biểu | ... | ... |
| Hạn chế/vật phẩm/tài nguyên | ... | ... |
| Những bí mật chưa được tiết lộ | ... | ... |

### CANON_WORKING — chi tiết đang thử

| Nội dung | Xuất hiện ở đâu | Mức chắc chắn | Cần chốt? |
|---|---|---|---|
| ... | ... | ... | ... |

### OPEN_QUESTIONS

- [ ] ...

## E. CONTINUITY_LEDGER

| Mốc chương/cảnh | Thời gian | Địa điểm | Nhân vật hiện diện | Trạng thái/tài nguyên | Điều đã biết | Nút truyện còn treo |
|---|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... | ... |

## F. AUTHOR_FEEDBACK — quy tắc học từ chỉnh sửa đã duyệt

| ID | Đoạn gốc (trích ngắn) | Vấn đề | Đoạn sửa đã duyệt | Bài học/tác dụng | Phạm vi | Trạng thái |
|---|---|---|---|---|---|---|
| FB-001 | ... | ... | ... | ... | project/character/scene | đề xuất/đã duyệt |

**Nguyên tắc:** chỉ quy tắc **đã duyệt** mới được dùng như chuẩn chính thức của dự án; ví dụ một câu bị nhận xét “văn AI” cần ghi lại nguyên nhân cụ thể, không mặc nhiên cấm cả một thủ pháp.

## G. Lịch sử cập nhật

| Ngày/phiên bản | Điều thay đổi | Người duyệt | Chương bị ảnh hưởng |
|---|---|---|---|
| ... | ... | ... | ... |


## H. Cấu hình ghi nhớ và chapter-close audit (v3)

- `AUTO_LEARN_STYLE`: true / false (mặc định true)
- `STORE_CONFIRMED_AUTHOR_PREFERENCES`: true / false
- `STORE_INFERRED_PREFERENCES_AS_CANDIDATE`: true / false
- `CHAPTER_CLOSE_CUMULATIVE_AUDIT`: true (**mặc định true; mỗi chương 1→N**)
- `AUDIT_COVERAGE`: auto (full-text nếu có thể, không thì 100% index + raw bằng chứng) / full-text-only
- `REQUIRE_AUTHOR_APPROVAL_TO_COMMIT_CANON`: true (mặc định)
- `FULL_TEXT_DEEP_AUDIT_PERIOD`: tùy chọn mỗi 5/10 chương, bổ sung chứ không thay thế audit lũy tích mỗi chương
- `PERSISTENCE_BACKEND`: file / database / chat-only
- `STORY_DATA_ROOT`: projects/<project_id>/
- `ON_BLOCKER`: stop, đề xuất sửa, yêu cầu tác giả duyệt hoặc override

Lưu ý: Trong `chat-only`, skill chỉ tạo patch/snapshot để người dùng lưu. Không tự cam kết lưu bền vững hoặc đã đọc lại mọi chương nếu không có dữ liệu nguồn.
