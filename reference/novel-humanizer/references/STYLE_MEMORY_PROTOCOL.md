# STYLE MEMORY PROTOCOL — v3.0

## Mục tiêu

Ghi lại **phong cách mà tác giả thực sự lựa chọn** để dùng lại trong các chương và phiên làm việc sau, không cần người dùng lặp lại, không làm đồng nhất các thể loại. Chỉ nói "đã nhớ" khi đã ghi thành công vào tệp/DB có thể đọc lại.

## Ưu tiên và phạm vi

- `project`: khung văn phong chung cho một bộ truyện; `arc`, `chapter`, `scene`: ghi đè cục bộ; `character_voice`: giọng nói riêng từng nhân vật; không trộn lẫn giọng người kể.
- `explicit`: lời tác giả khẳng định, `approved_sample`: đoạn chuẩn được duyệt, `approved_edit`: sửa đổi được chấp thuận, `observed_edit`: thay đổi tác giả trực tiếp nhưng chưa có giải thích, `inferred`: giả thuyết kỹ thuật của AI.
- Trạng thái: `confirmed`, `candidate`, `rejected`, `superseded`. Chỉ `confirmed` có hiệu lực như luật; `candidate` chỉ là gợi ý mềm để tránh hỏi thừa, không dùng đè luật cũ.
- `strength`: `HARD`, `PREFERRED`, `AVOID`, `OPEN`. Một đặc điểm cụ thể như "nhân vật A hay nói lắp" không được suy thành "toàn truyện nói lắp".

## Ghi nhớ ngay khi tác giả phản hồi

1. Nhận lời nói/đoạn mẫu/diff; lưu nguyên văn phần chứng cứ ngắn cần thiết và ngữ cảnh.
2. Trích xuất *thủ pháp* (nhịp đoạn, giọng nhân vật, mức ẩn dụ, độ nén, phương thức biểu đạt, chữ dùng...), phân biệt **lỗi nội dung** với **sở thích hình thức**.
3. Phân loại `confirmed` nếu tác giả **chủ động nói rõ mong muốn** hoặc đã chấp thuận lựa chọn; nếu AI tự suy ra thì `candidate`.
4. Xác định `scope`, `attribute`, `polarity`, `strength`, `why`, `positive_example`/`negative_example` (nếu có).
5. Append event vào `AUTHOR_FEEDBACK.jsonl`; cập nhật `STYLE_MEMORY.json` và bản tóm tắt trong profile nếu có ghi quyền, giữ bản trước trong backup/version.
6. Đọc lại tệp để kiểm tra cập nhật, thông báo rất gọn thành công. Nếu không thể ghi thì xuất `STYLE_MEMORY_UPDATE`, ghi rõ `CHƯA LƯU BỀN VỮNG`.

## Học tự động từ tác giả sửa chữ

Khi app có *original/revised diff* của tác giả, tạo quy tắc candidate với hai câu trích ngắn và lý do đề xuất. Tối thiểu hai ví dụ độc lập cùng một hướng mới có thể đề xuất nâng lên project; chỉ nâng thành rule hard hoặc cấm chung khi tác giả duyệt, không dùng tần suất làm chứng cứ duy nhất. Một bản sửa do AI tự sinh **không** được coi là phản hồi tác giả.

## Điều chỉnh và rollback

- Khi yêu cầu mới xung đột với rule cũ, giữ provenance; nếu tác giả chủ động đổi gu thì `superseded` rule cũ, không âm thầm xóa chứng cứ.
- Khi tác giả từ chối một quy tắc, `rejected` và ghi lý do; không tái đề xuất lỗi tương tự liên tục.
- Chương đã được duyệt giữ nguyên trừ khi tác giả yêu cầu rà phong cách ngược; việc cập nhật style chỉ chi phối đoạn viết tiếp theo mặc định.
- Rule có `confidence` chưa chắc không được nâng trạng thái bằng cách tự tăng số điểm tùy ý.

## Ví dụ record (mang tính minh họa)

```json
{
  "id": "ST-001",
  "attribute": "narration.paragraph_rhythm",
  "preference": "Gộp hành động và suy nghĩ liền mạch vào cùng đoạn; tránh một câu một đoạn liên tục",
  "polarity": "prefer",
  "strength": "PREFERRED",
  "scope": {"type": "project", "id": "truyen-a"},
  "source": "explicit",
  "evidence": "Tác giả: các câu cùng ý nên nằm chung đoạn",
  "approved_by": "author",
  "status": "confirmed",
  "updated_at": "2026-10-12"
}
```

## Trong Gemini Web/App và môi trường chỉ có chat

Có thể nạp tệp làm ngữ cảnh để **đọc**, nhưng skill Markdown không tự ghi trở lại tệp đính kèm hoặc đảm bảo tồn tại xuyên phiên. Sau thay đổi, yêu cầu AI đưa ra nội dung profile mới/patch để người dùng thay thế tệp cũ, hoặc dùng app/agent có công cụ ghi tệp/API thực sự.
