# CUMULATIVE CONTINUITY & LOGIC AUDIT — v3.0

## Cam kết phạm vi

**Sau mỗi chương N, bao phủ lịch sử chương 1→N** để kiểm tra dữ kiện và diễn biến. "Bao phủ từ đầu" nghĩa là mọi chương đều nằm trong lần rà, không đồng nghĩa AI chắc chắn đã đọc lại *toàn văn* khi truyện hàng triệu từ. Báo cáo minh bạch `FULL_TEXT`, `HYBRID_100_PERCENT_INDEX` hay `PARTIAL`.

## Chuẩn bị

- Nạp **tất cả** chương từ CH001 đến CHN, phiên bản đã duyệt và bản đang QC.
- Kiểm tra hash bản gốc so với `CHAPTER_INDEX`. Tóm tắt hay ledger gắn hash cũ là **STALE**.
- Nạp `STORY_BIBLE`, `STYLE_MEMORY`, `CONTINUITY_LEDGER`, open threads, những override đã chốt.
- Nếu thiếu chương, đánh dấu `PARTIAL` và không công bố "QC toàn truyện PASS".

## Hai lượt kiểm bắt buộc

### A. Forward pass — dòng thời gian phát triển

Qua từng chương 1→N, theo dõi:

1. Mốc thời gian (tương đối và tuyệt đối), đi lại, khoảng cách, lịch trình, sự kiện đồng thời.
2. Vị trí và hiện diện; cùng thời điểm có thể ở hai nơi hay không.
3. Trạng thái sống/chết, sức khỏe, thương tích, hồi phục; ngoại hình hoặc tuổi có nguyên nhân.
4. Vật phẩm, tiền tệ, tài nguyên, người sở hữu, trao đổi, tiêu hao, cooldown/cấp bậc.
5. Điều từng nhân vật biết, đã chứng kiến hoặc chỉ nghe kể; ngôi kể và luồng tiết lộ cho độc giả.
6. Thế giới và luật: công nghệ, phép thuật, tu luyện, địa lý, tập tục, tổ chức.
7. Nhân quả, động lực, quyết định, hệ quả đã được thiết lập và được trả giá hay chưa.
8. Tình tiết mở, bí mật, manh mối, foreshadow, lời hứa, deadline, kết quả được chờ đợi.
9. Phong cách đã xác nhận, giọng thoại và ngoại lệ đúng cảnh. Không biến khác biệt có chủ đích thành lỗi.

### B. Backward pass — truy lại từ chương mới

Từ mọi tiết lộ/đổi trạng thái ở N, hỏi: "Điều này có làm CH001..CH(N−1) bất khả thi, vô nghĩa hoặc buộc nhân vật trước kia đã phải biết gì đó mà họ không biết không?" Với bất đồng, truy về chương gốc và kiểm tra ngữ cảnh trực tiếp.

Ví dụ kiểm tra:
- Chương 9 bảo nhân vật chưa bao giờ gặp B nhưng chương 3 có cảnh gặp thật.
- Chương 12 dùng phép khi chương 2 khóa luật cần tài nguyên đã cạn ở chương 11.
- Chương 20 tiết lộ danh tính phản diện; chi tiết đó **không bắt buộc** là lỗi nếu trước đó là nói dối/nhầm lẫn được thiết lập hợp lý.
- Kết quả rơi từ trên trời xuống mà không có cơ sở từ chương trước là nghi vấn setup/payoff, không phải chắc chắn vi phạm định luật thế giới.

## Cách đánh giá vấn đề

| Severity | Quy tắc | Hành động |
|---|---|---|
| BLOCKER | Xung đột chắc chắn với canon/hành động/điều kiện cứng; thiếu chương cần thiết để xác minh một chi tiết quyết định | Ngăn duyệt mặc định, sửa hoặc yêu cầu tác giả override có giải thích |
| MAJOR | Lỗ hổng nhân quả, tri thức nhân vật/động lực thiếu nền, retcon mập mờ | Sửa/giải thích hoặc tác giả chấp thuận ngoại lệ |
| MINOR | Thời gian diễn đạt chưa rõ, cách xưng hô/chi tiết nhỏ, nhịp và lặp gây xao nhãng | Đề xuất chỉnh vùng nhỏ |
| INTENTIONAL_OR_UNKNOWN | Twist có chủ ý, người kể không đáng tin, bí mật chưa lộ, chứng cứ chưa đủ | Ghi theo dõi; không tự sửa canon |

Mỗi finding cần `issue_id`, `severity`, `chapters`, `evidence` gồm các trích dẫn ngắn có vị trí, `logic`, `confidence`, `counter_explanation`, `suggested_minimal_fix`, `author_decision_required`, `status`. Không viện dẫn trích đoạn chưa mở xem. Phân biệt **mâu thuẫn** với **thay đổi theo thời gian**; ledger nên lưu thời điểm hiệu lực, không chỉ giá trị cuối.

## Thuật toán với truyện dài

- Mặc định: quét 100% hồ sơ từng chương với facts/timeline, mở toàn văn các đoạn liên quan, cập nhật chỉ mục nếu thiếu; gọi `HYBRID_100_PERCENT_INDEX`.
- Nếu còn đủ tài nguyên xử lý: đọc lại nguyên văn CH001..CHN, đánh `FULL_TEXT`.
- Nếu thiếu hồ sơ chương, không thể mở đoạn liên quan hoặc mất ngữ cảnh: `PARTIAL` + danh sách lỗ hổng. Không âm thầm tự điền từ trí nhớ mô hình.
- Nên thực hiện full-text *deep audit* theo yêu cầu hoặc sau một mốc chương (ví dụ 5–10 chương); mốc này **bổ sung**, không thay thế lượt cumulative audit sau **từng chương**.
- Index/tóm tắt chỉ là công cụ tăng tốc; không phải chứng cứ đủ mạnh để giải quyết mâu thuẫn cụ thể giữa các câu. Truy nguồn chương gốc khi có tranh chấp.

## Giao bản thảo, sửa và commit

`Draft N → nội chương QC → forward+backward 1..N → issues → targeted corrections → chạy lại audit vùng liên quan → QC report → tác giả duyệt → commit canon/ledger`.

Không sửa âm thầm chương đã duyệt. Nếu phải sửa chương k cũ: đánh dấu audit/tóm tắt liên quan là `stale`, chạy lại từ k đến N và báo tổng ảnh hưởng.

## Mẫu báo cáo

Xem `templates/CHAPTER_QC_REPORT.md`. Một bản báo cáo ghi tối thiểu: N, phiên bản từng chương, phạm vi phủ 1..N, dạng coverage, danh sách chương chỉ được kiểm qua index, chương đã mở nguyên văn, lỗi theo mức, đường xử lý, trạng thái duyệt.
