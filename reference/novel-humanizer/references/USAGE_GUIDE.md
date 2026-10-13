# HƯỚNG DẪN — NOVEL HUMANIZER UNIVERSAL v3.0

> Hai tính năng trọng tâm: **STYLE MEMORY** (học sở thích và lưu phiên bản) và **CHAPTER-CLOSE CUMULATIVE QC** (mỗi chương xong đều kiểm truyện từ chương 1 đến chương mới).

## 1. Tệp nào dùng để nạp skill?

Gói có `SKILL.md` ở gốc, `references/`, `templates/`, `presets/` và `tools/`. Đừng dùng preset `quan-net-di-gioi.md` cho truyện khác; nó chứa dữ liệu riêng của bộ Quán Net Dị Giới.

- **Gemini App / Gemini Web hoặc chat không có quyền ghi:** tải `SKILL.md` (hoặc ZIP nếu giao diện có chức năng nhập Skills tương thích), tải thêm hồ sơ từng truyện và các chương khi cần. Skill có thể đọc và *đề xuất* cập nhật memory, nhưng không bảo đảm tự lưu thay đổi xuyên phiên. Sau mỗi lần đổi gu, nhận tệp/patch mới và tải lại.
- **Gemini CLI / công cụ agent có quyền đọc-ghi thư mục:** chép cả thư mục skill vào vị trí Skills mà môi trường đang hỗ trợ, **và** tạo thư mục `projects/<id>` bằng script hoặc bằng app. Agent có quyền ghi thì mới tự ghi file style/ledger thực sự.
- **ChatGPT Project / Gems:** nạp skill làm tài liệu hướng dẫn, kèm dữ liệu riêng của dự án. Khi không có cơ chế sửa tệp đính kèm, cập nhật tệp bằng tay hoặc thông qua app kết nối.
- **App Auto Story:** nên cài v3 vào pipeline chung; dùng hooks tại `references/APP_INTEGRATION.md`. Từng agent phải được cấp quyền và chính sách commit riêng.

**Nhớ:** `SKILL.md` không tự vận hành nền hay truy xuất truyện khi chưa được kích hoạt. Muốn kiểm tra ngay sau mỗi chương mà không cần nhắc lại, app phải gọi hook `onChapterDraftCompleted` hoặc tạo instruction cố định cho agent thực thi trước khi kết thúc lượt viết.

## 2. Ba cấp độ sử dụng

| Mức | Môi trường | Có tự lưu giọng? | QC chương 1→N? |
|---|---|---|---|
| Cơ bản | Chat thủ công | Không bảo đảm; AI xuất bản cập nhật để lưu | Có, **nếu** người dùng cung cấp toàn bộ dữ liệu cần thiết |
| Có tệp | CLI/agent có quyền ghi | Có, tệp theo project | Có, theo hồ sơ 100% chương và nguyên văn theo tài nguyên |
| App tích hợp | Auto Story + DB + hooks | Có, tự ghi khi người dùng phản hồi/duyệt | Tự kích hoạt sau **mỗi** chương, chạy hai vòng và lưu QC report |

## 3. Tạo một truyện mới với bộ nhớ riêng

Một dự án nên có cấu trúc sau:

```text
projects/truyen-a/
  PROJECT_PROFILE.md
  STORY_BIBLE.md
  STYLE_MEMORY.json
  AUTHOR_FEEDBACK.jsonl
  CHAPTER_INDEX.json
  CONTINUITY_LEDGER.json
  chapters/
    CH001.md
    CH002.md
  qc_reports/
    CH001_QC.md
    CH002_QC.md
```

Trong terminal có Python 3, có thể tạo bộ khung bằng:

```bash
python tools/novel_state.py init --project projects/truyen-a --project-id truyen-a
```

Trong thư mục dự án, chỉnh `PROJECT_PROFILE.md` cho phù hợp. Bản mẫu không yêu cầu điền hết; có thể bắt đầu bằng một ý tưởng và 1–2 đoạn văn mẫu.

### Prompt đầu dự án

```text
Nạp Novel Humanizer Universal v3 và mở project `truyen-a`.
Hãy đọc PROJECT_PROFILE, STORY_BIBLE, STYLE_MEMORY, CHAPTER_INDEX
và CONTINUITY_LEDGER mới nhất trước khi viết.
Thể loại: [v...]. Văn phong tôi muốn: [...].
Tự học sở thích mà tôi CHỦ ĐỘNG nói rõ; những gì chỉ suy ra thì lưu candidate.
Tôi muốn kiểm tra continuity + logic tích lũy từ CH001 sau MỖI chương.
Đừng tự duyệt thay tôi hay tự sửa canon chương cũ.
```

## 4. "Tự nhớ văn phong" hoạt động như thế nào?

### Tình huống 1 — Tác giả trực tiếp nói sở thích

> Từ nay với truyện A, tôi thích trần thuật thành các đoạn liền mạch, không xuống hàng sau mỗi hành động nhỏ. Thoại nhân vật B phải ngắn, ngập ngừng hơn.

Agent ghi thành hai quy tắc `confirmed` ở scope `project` và `character_voice:B` nếu có nơi lưu. Khi lần sau viết, chúng có hiệu lực ngay. Không cần hỏi duyệt lại.

### Tình huống 2 — Tác giả sửa một đoạn nhưng chưa giải thích

> Tác giả đổi ba câu giàu ẩn dụ thành hai câu trực tiếp.

Agent **không được** kết luận toàn truyện "cấm ẩn dụ". Ghi một giả thuyết `candidate` và so với ví dụ khác. Nếu tác giả nói "đúng, từ nay đừng dùng ẩn dụ ở các đoạn đánh nhau", lúc ấy mới chuyển thành `confirmed` trong scope `scene_type:combat`.

### Tình huống 3 — Tác giả khoanh lỗi kiểu "văn AI"

```text
MODE=STYLE_TUNE.
Đoạn sai: "[trích đoạn]".
Lỗi tôi không thích: lời kể lặp ý nghĩa cảnh, như người dẫn chương trình.
Muốn sửa: giữ hành động, bỏ câu tổng kết triết lý.
Phạm vi: toàn dự án này, ngoại trừ những đoạn nội tâm có chủ đích.
Hãy sửa và lưu đây là rule confirmed. Báo rõ đã ghi file hay chưa.
```

Nếu file/DB không ghi được, agent tạo khối `STYLE_MEMORY_UPDATE` để bạn lưu tay rồi tải lên phiên sau; không nói "đã nhớ vĩnh viễn".

## 5. Quy trình mỗi lần viết xong một chương

```text
Nạp bộ nhớ/canon + lịch sử chương
     ↓
Viết CH-N (DRAFT)
     ↓
QC nội chương + trích facts/scene/timeline
     ↓
CHAPTER-CLOSE CUMULATIVE AUDIT (CH001...CHN)
     ├─ Forward: theo dõi sự kiện, vị trí, vật phẩm, tri thức, luật thế giới
     └─ Backward: sự thật mới có phá logic chương cũ không?
     ↓
BLOCKER/MAJOR? → chỉ sửa cục bộ hoặc xin quyết định
     ↓
Kiểm tra regression sau sửa
     ↓
Báo cáo QC và bản chương cho tác giả duyệt
     ↓
Approved? → lưu bản chốt, commit facts, index, feedback
```

Bất kể chương mới ngắn hay dài, lần QC đều **kiểm tất cả hồ sơ chương từ 1 đến N**. Với truyện vừa đủ ngữ cảnh, đọc lại toàn văn. Với truyện quá dài, dùng hồ sơ chương và mở raw evidence nơi nghi ngờ; báo `HYBRID_100_PERCENT_INDEX`. Không báo `FULL_TEXT` khi chưa đọc toàn văn.

### Prompt viết chương mới

```text
MODE=WRITE + CHAPTER_CLOSE_QC. Viết chương 12 theo outline đính kèm.
Giữ đúng phong cách đã lưu trong STYLE_MEMORY.
Sau khi viết, chạy QC nội chương rồi rà continuity/logic TỪ CHƯƠNG 1 ĐẾN 12.
Kiểm tra cả việc chương 12 có làm các chi tiết chương 1–11 trở nên vô lý hay không.
Không chỉ đối chiếu chương 11. Nêu issue có bằng chứng, không tự retcon.
Lưu báo cáo QC riêng, không chen giải thích vào nội dung truyện.
Chỉ đưa chương vào canon khi tôi duyệt.
```

### Prompt buộc kiểm lại truyện từ đầu

```text
MODE=CUMULATIVE_AUDIT, through=25.
Rà toàn bộ CH001..CH025, không bỏ qua chương nào.
Nếu có đủ văn bản, đọc lại toàn văn. Nếu không đủ, rà 100% chapter indexes,
truy raw các chỗ nghi vấn và báo rõ coverage HYBRID hoặc PARTIAL.
Kiểm theo timeline, nhân quả, di chuyển, tài nguyên, thương tích,
tri thức nhân vật, luật thế giới, các nút truyện còn mở và POV.
Mỗi mâu thuẫn phải dẫn chương/đoạn hai phía. Không sửa nguyên bản khi tôi chưa duyệt.
```

## 6. Sử dụng script lưu trạng thái (trong ZIP)

Script tiêu chuẩn Python để **ghi file, ghi log và kiểm tra tính toàn vẹn**, không phải model tự đọc hiểu tiểu thuyết.

```bash
# Lưu bản chương vừa được Writer tạo
python tools/novel_state.py register-chapter \
  --project projects/truyen-a --chapter 1 --file draft_01.md

# Agent đọc chương 1 và tạo chapter01_index.json với summary, scenes...
python tools/novel_state.py index-chapter \
  --project projects/truyen-a --chapter 1 --file chapter01_index.json

# Kiểm đủ các tệp/chương 1..N và hash đã thay đổi chưa
python tools/novel_state.py preflight \
  --project projects/truyen-a --through 1

# Agent QC ngữ nghĩa thực tế → xuất CH001_QC.md và qc_meta.json
python tools/novel_state.py record-audit \
  --project projects/truyen-a --meta qc_meta.json --report CH001_QC.md

# Sau khi tác giả DUYỆT chương và QC PASS, mới đổi trạng thái
python tools/novel_state.py approve-chapter \
  --project projects/truyen-a --chapter 1
```

Ví dụ `chapter01_index.json` (được tạo **sau khi đọc văn chương**):

```json
{
  "summary": "Nhân vật A tới thị trấn, mất túi tiền và gặp B.",
  "scenes": [{"id": "CH001-S1", "location": "Cổng thị trấn", "characters": ["A"]}],
  "time_markers": ["Ngày 1, chiều"],
  "characters": ["A", "B"],
  "fact_refs": ["F001", "F002"],
  "open_threads": ["Ai lấy túi tiền?"]
}
```

Ví dụ `qc_meta.json` (do agent QC ghi **đúng theo phạm vi thật**):

```json
{
  "chapter_id": 1,
  "coverage": "FULL_TEXT",
  "covered_chapters": [1],
  "raw_read_chapters": [1],
  "result": "PASS",
  "issues": []
}
```

Với chương N lớn, liệt kê `covered_chapters: [1,2,...,N]`; `FULL_TEXT` chỉ khi `raw_read_chapters` thực sự có mọi chương. `record-audit` xác minh khai báo cấu trúc, **không xác minh việc LLM có thật sự đọc đủ toàn văn**.

Để ghi feedback từ tệp JSON:

```bash
python tools/novel_state.py feedback --project projects/truyen-a --file feedback.json
```

Ví dụ `feedback.json`:

```json
{
  "source": "explicit_author_instruction",
  "author_comment": "Từ nay ít dùng câu tổng kết kiểu trailer ở cuối cảnh.",
  "rule": {
    "id": "ST-001",
    "attribute": "scene_ending",
    "preference": "Kết bằng hành động/câu hỏi thật thay vì lời báo trước biến cố",
    "strength": "PREFERRED",
    "scope": {"type": "project", "id": "truyen-a"}
  }
}
```

## 7. Khi sửa chương cũ

Chương 3 thay đổi nhưng truyện đã đến chương 40 → đăng ký lại chương 3 bằng `--replace`, hệ thống đánh dấu audit các chương ≥3 là `stale`. Sau đó cần chạy lại semantic audit theo dòng 1..40 trước khi coi trạng thái dự án hợp lệ. Đừng chỉ sửa summary mà không đọc lại chương thật.

## 8. Chọn chế độ: Auto Story và Assist

**AUTO**: AI viết → QC nội chương → QC lũy tích 1..N → sửa tối thiểu → QC lại → chờ tác giả duyệt (hoặc auto-approve nếu tác giả bật). Nếu lỗi `BLOCKER`, app nên tạm dừng chuyển chương tiếp theo.

**ASSIST**: AI góp ý/rewrite vùng tác giả chọn. Nếu vùng đó khiến một chương hoàn tất hoặc thay nội dung chương đã duyệt, gọi lại cumulative audit. Tác giả có quyền giữ một dụng ý khác thường dù QC gợi ý đổi.

Đối với app, nên lưu revision và snapshot ở DB/FS, dùng lock hoặc optimistic version để nhiều agent không đồng thời ghi profile, và tạo nút **"Xem những gì AI đã học về giọng văn"**, **"Huỷ quy tắc"**, **"Audit từ chương 1"**, **"Xem ảnh hưởng sửa chương cũ"**.

## 9. Kiểm thử nhanh trước khi chạy thật

1. Cho skill viết 1 đoạn tiên hiệp cổ phong, sau đó truyện đô thị hài: quy tắc không lẫn nhau.
2. Nói rõ "đừng một câu một đoạn" → kiểm tra rule `confirmed` đã ghi file và được nạp khi viết tiếp.
3. Sửa một đoạn riêng → rule chỉ nên ở trạng thái `candidate` nếu chưa rõ chủ đích.
4. Tạo lỗi CH001 nói nhân vật ở Hà Nội, CH005 lại nói cùng giờ đang ở Đà Nẵng mà không có dịch chuyển: QC phải dẫn nguồn hai chương.
5. Cho nhân vật nói dối có chủ đích; QC không tự xem câu nói dối là canon thật.
6. Thay chương 2 sau khi hoàn thành chương 10: hệ thống phải phát hiện hash đổi, invalidate hồ sơ liên quan và đòi kiểm lại.
7. Cố ý thiếu CH004 khi viết đến CH006: QC phải báo PARTIAL, không đánh PASS toàn truyện.

## 10. Giới hạn quan trọng

- Nếu **không có toàn bộ chương hoặc index đủ tin cậy**, không thể kết luận nhất quán toàn truyện.
- Nếu ngữ cảnh quá lớn, dùng index toàn bộ + mở nguyên văn có chọn lọc; đây không phải đọc lại toàn văn.
- Nếu **không có quyền ghi**, skill không tự lưu bền vững. Cần app/CLI có storage hoặc tác giả tải lại tệp sau cập nhật.
- Script trong gói không thay thế LLM hoặc biên tập viên cho việc kiểm logic, không tạo bảo đảm \"không còn lỗi\".

**Nguyên tắc cuối:** Tác giả chọn giọng văn → skill học theo bằng chứng và lưu nếu có quyền → viết từng chương → mỗi chương QC nội bộ và soát ngược từ chương đầu → tác giả duyệt → commit.
