# BÁO CÁO CHỨC NĂNG & MÔ PHỎNG NGƯỜI DÙNG
## Story OS — dự án "Những Cuộc Tình Tải Xuống" (69 chương)

*Biên bản dogfooding: vận hành app như một tác giả thật, ghi lại mọi chức năng đã dùng, lỗi gặp, và giới hạn quy trình. Đối chiếu `BIEN_BAN_VAN_HANH.md` (A1–A7, C1–C23) cho chi tiết lỗi.*

---

## A. INVENTORY CHỨC NĂNG — đã kiểm chứng trong phiên

### 1. Sinh truyện tự động (authoring engine)

| Chức năng | Tầng | Đã dùng | Kết quả |
|---|---|---|---|
| Authoring run `flow=rolling`, `goal_mode=end`, `target_chapters` | Project | ✓ | Sinh 69 chương theo sóng; target đổi giữa chừng 85→69 qua DB |
| `chapter_outline` (dàn chương → `Tên cảnh — beat`) | Arc/wave | ✓ | Hint tác giả inject được qua `wave_hint` — điều khiển số chương + nội dung |
| `chapter_scenes` (dàn cảnh trong chương) | Chapter | ✓ | 6–8 cảnh/chương, beat đi thẳng vào prompt viết |
| `scene_write` | Scene | ✓ | ~2800–3900 ký tự/cảnh; sửa skeleton = lái nội dung không đụng prose |
| `chapter_facts` (trích dữ kiện) | Chapter | ✓ | Sau fix: trích theo cảnh, tolerate lỗi từng cảnh |
| Checkpoint `pause_after_wave` | Wave | ✓ | Dừng ranh giới hồi → approve + hint → hồi mới |
| `resume` sau lỗi provider/cold restart | Run | ✓ | Xoá `failed`+`interrupted` → chạy tiếp đúng chỗ dở |

### 2. Thao tác tác giả (author-first)

| Chức năng | Đã dùng | Ghi chú |
|---|---|---|
| Sửa prose tay (PATCH scene, auto-snapshot `scene_versions`) | ✓ | Nhiều lần: sửa ngày drift, chèn dòng mục tiêu, sửa vai đảo |
| `POST /scenes/{id}/ai-fix` (AI viết lại/expand có preview) | ✓ | 2 cảnh lớn: nụ hôn bếp (2980→5078c), flashback thân mật (3128→5880c) |
| Sửa skeleton cảnh trước khi engine viết | ✓ | Ch14: 5 cảnh chèn beat tarot/đũa/điện thoại úp → ăn vào prose |
| `POST /chapters/insert` + `DELETE ?compact` | ✓ | Insert/delete test ở đuôi, khép trục sạch |
| `POST /chapters/{id}/reextract` | ✓ | Trích lại ch1 sau sửa prose — wipe AI-facts, giữ author/locked |
| `POST /chapters/{id}/deep-check` | ✓ | Tìm được lỗi vai đảo thật; nhưng timeout đồng bộ >4ph (C10) |
| Bình luận/Discussion threads | ✓ | Nhiều note tác giả: ch19, ch21, ch29–31… |
| Pin message trong thread | ✓ | Đánh dấu quyết định biên tập |

### 3. Trí nhớ truyện & Canon

| Chức năng | Đã dùng | Ghi chú |
|---|---|---|
| `story_summaries` 5 tầng (scene→chapter→arc→volume→story) | ✓ | Chạy backlog generate + coverage — 10/10 tầng cao xong |
| Context manifest (`POST ai/context-manifest`) | ✓ | Xem được included/omitted — dùng để debug prompt |
| Review Queue (`suggested_changes`) | ✓ | 36 duyệt / 7 từ chối — extraction KHÔNG tự thành Canon |
| `scene_versions` (snapshot/restore) | ✓ | Tự snapshot trước mọi sửa prose |
| Characters + aliases, secret fields | ✓ | Tạo Thế Anh + secret + alias |
| Threads + `planned_payoff_order` + `thread_beats` | ✓ | 117 Hố; beats inject đúng mốc chương; **payoff chỉ là gợi ý, không bắt buộc** (C12); đánh RESOLVED thủ công sau audit (C23) |
| `Ability` (kĩ năng nhân vật) ghim qua `cast_json.abilities` | ✓ | "Nói Lời Mê Hoặc" ghim 4 chương Thế Anh — prose đổi đúng hướng thao túng |

### 4. Kiểm tra & tín hiệu

| Chức năng | Đã dùng | Kết quả |
|---|---|---|
| `/continuity/check` deterministic | ✓ | 0 issues sau dọn conflict; flag đúng CANON/STATE conflict |
| `signals` (thread im lặng/quá hạn) | ✓ | Báo Thế Anh `never` xuất hiện trước khi vào truyện |
| KNOWLEDGE_LEAK / LOCATION_DRIFT | ✓ | 2 false positive đã verify, giữ nguyên |

### 5. Đọc & xuất

| Chức năng | Đã dùng |
|---|---|
| `/read` reading mode theo chương | ✓ |
| `/search?q=` (scene/chapter/char/canon/thread/event/location) | ✓ |
| `TimelineView` 3 chế độ | ✓ |
| Export JSON (backup toàn project) + Markdown (bản thảo) | ✓ |
| `GET/DELETE /ai/turns` + prune | ✓ |

---

## B. DIỄN BIẾN MÔ PHỎNG (tóm tắt sóng)

- **Sóng 1–2 (ch1–13)**: mở đầu — nhóm 5 cô, luật khoe, file "Mục", Bảo/My, ghế thứ năm. Pilot chưa có; vận hành tay.
- **Sóng 3 (ch14–19)**: "Biên Bản Đầu Tiên" — Trang–Linh nụ hôn đầu (sửa tay + ai-fix), Hạnh trốn về nhà Linh, hồ sơ trống.
- **Sóng 4 (ch20–24)**: khép Quyển 1 — "Hai Vạch": que thử của Linh + Hạnh gõ cửa.
- **Sóng 5 (ch25–33)**: "Hậu Quả" — Mục 001=Bảo (đối chiếu ảnh), tarot/Thế Anh vào cuộc (skill pin ch28/32), Que Kem literal, phòng trị liệu 30 triệu.
- **Sóng 6 (ch34–41)**: "Người Đứng Phía Sau" — thiệp cưới, đêm nhiều phòng cắt nóng/lạnh, Ba Mươi Triệu chuyển khoản, ch41 mục 019 **được viết sẵn vào file của Linh**.
- **Sóng 7 (ch42–47)**: "Đối Diện" — Nam trở về đúng lúc dở nhất, Khôi biết brief sữa trong file khoá.
- **Sóng 8 (ch48–54)**: "Tình Yêu Không Tải Được" — phòng khám Q7, "con có bầu, không biết bố là ai" trước mẹ, đọc to danh sách giữa nhóm.
- **Sóng 9 (ch55–69)**: "Cập Nhật" — endgame trả Hố: Ngăn khóa kéo→Số Lạ→Nam→Đám Cưới Đổ→Chìa Khoá Trả Lại→Người Rời Thành Phố→Xoá file→Ghế Thứ Năm. **Đổi model giữa sóng**: ch55–67 deepseek-v4.1-flash, ch68–69 qwen3.8-flash (qua SSE stream — A6). Engine vượt target: outline thêm ch70–75 ngoại truyện trước khi pause tay → xoá bằng `delete_chapter_full` (phát hiện bug A7 + C22).

---

## C. NHỮNG GÌ CHỨNG MINH ĐƯỢC

1. **Two-way workflow chạy thật**: tác giả viết/sửa → AI expand → tác giả duyệt; AI viết cả chương → tác giả sửa tay từng đoạn → cả hai cùng có trong bản cuối.
2. **Wave-hint lái truyện hiệu quả**: mọi chủ đề yêu cầu (18+, que kem, tarot scam, kịch tính/tha thứ/chia xa) đều ăn vào outline đúng hồi được gieo.
3. **Sửa skeleton ≠ sửa prose**: can thiệp trước-khi-viết (skeleton) và sau-khi-viết (ai-fix/PATCH) là hai lever riêng, đều hoạt động.
4. **Hố mở được giữ dài**: thread từ ch1–10 (số lạ, dây buộc tóc, ghế thứ năm, ngăn khóa kéo) sống tới ch55–69 nhờ `planned_payoff_order` annotate vào prompt — NHƯNG không có enforcement (C12).
5. **Kĩ năng nhân vật hoạt động khi được ghim**: đổi văn phong cảnh đúng hướng — nhưng không tự kích hoạt (C11).
6. **Resilience thật**: provider 504 hàng loạt → `interrupted` không giết run; cold restart → `paused` → resume sạch.
7. **Đổi model giữa run được, giọng văn không đứt**: 868 turn DeepSeek + 26 turn Qwen; ch68–69 (Qwen) giữ đúng format file Mục, motif, trạng thái truyện — context pipeline (summary+canon+constraints) mang giọng qua ranh giới model.
8. **SSE stream vượt gateway 60s**: non-stream 504 vĩnh viễn với call dài; `stream:true` sống qua ngưỡng (bytes chảy liên tục) → vá provider-level, toàn bộ task hưởng lợi (A6).
9. **Endgame audit bằng tay hoạt động nhưng vất**: merge 17 thread trùng + mark 40 RESOLVED — đúng việc "resolution sweep" app nên tự làm (C12/C23).

---

## D. SỐ LIỆU CUỐI

| Chỉ số | Giá trị |
|---|---|
| Chương / cảnh | **69 / 468** (đúng target sau khi xoá 6 chương vượt) |
| Prose | **1.521.240 ký tự** (~2.900–3.900 c/cảnh) |
| Authoring steps | 623 done (run `27146f7a`, pause ở 69 theo ý tác giả) |
| AI turns | 894 — deepseek-v4.1-flash 868 + qwen3.8-flash 26 |
| Threads | 117 tổng — 40 RESOLVED, 52 OPEN (gồm ambiguity chủ đích), 25 MERGED |
| Review queue | 36 approved / 7 rejected / 0 pending |
| Characters / Canon facts | 12 / 1.005 |
| Verification | pytest **158 pass**, `tsc --noEmit` sạch, export JSON 12.6MB + MD 2MB, search/read 200 |

## E. GIỚI HẠN ĐÃ GHI NHẬN (chi tiết ở BIEN_BAN_VAN_HANH.md)

- A1–A7 (bug đã vá trong phiên): facts theo cảnh, interrupted-resume, JSON schema drift, interrupted-vs-failed, stale code, **SSE stream cho gateway 60s**, **shift_narrative hướng delta**.
- C1–C23 (vận hành/quy trình): extraction timeout & thread trùng; cast_json format; pause_after_wave tự reset; deep-check đồng bộ timeout; skill không tự ghim; không có resolution-sweep bắt buộc trả Hố + đánh RESOLVED tự động; drift chi tiết liên chương thoát checker; **engine không hard-stop ở target_chapters**; theo dõi payoff beat không đáng tin.

## F. ĐỀ XUẤT ƯU TIÊN (từ vận hành thật)

1. **Hard-stop theo target_chapters** — sau mỗi sóng, nếu `chapter_count >= target` → run done (C22).
2. **Resolution sweep trước hồi cuối** — liệt kê OPEN thread quá hạn, bắt outline trả hoặc tác giả tick "để ngỏ" (C12+C23).
3. **Dedupe thread sau extraction** — title/motif gần giống → gợi ý merge qua Review Queue (C17).
4. **Ability ↔ Character link** — auto-suggest ghim khi skeleton nhắc chủ sở hữu (C11).
5. **Deep-check → background job** có poll status (C10).
6. **Checker "title vs content" + fact drift liên chương** (C13/C14).
7. **Giữ đường SSE stream** cho mọi gateway có non-stream cutoff; hiển thị model+latency trên AI panel (C20).

---

*Cập nhật cuối: **run hoàn tất ở 69 chương**. Ch68–69 (Qwen) đã verify tay — motif "ghế thứ năm" khép đúng, file bị xoá, 3 app hẹn hò tắt từ tháng Ba.*
