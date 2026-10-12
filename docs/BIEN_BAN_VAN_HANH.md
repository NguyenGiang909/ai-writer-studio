# BIÊN BẢN VẬN HÀNH — phiên mô phỏng người dùng trên "Những Cuộc Tình Tải Xuống"

Bản ghi lỗi/khó khăn phát hiện khi vận hành app như một tác giả thật (AI chạy sóng,
người sửa, duyệt sóng, trích dữ kiện, kiểm tra continuity). Mục đích: tìm bug,
nâng cấp quy trình — không chỉ tạo truyện.

Cập nhật: **run `27146f7a` xong — 69 chương / 468 cảnh / 1.521.240 ký tự prose**
(868 turn deepseek-v4.1-flash + 26 turn qwen3.8-flash; ch68-69 viết bằng Qwen qua SSE stream).

---

## A. LỖI ĐÃ SỬA TRONG PHIÊN (code/backend)

| # | Lỗi | Triệu chứng | Cách sửa | File |
|---|---|---|---|---|
| A1 | `chapter_facts` gửi toàn bộ prose chương (~16-24K ký tự) 1 call | Gateway KiraAI cắt ~60s → 504 vĩnh viễn, step không bao giờ qua | Trích **theo từng cảnh** (~3K/call), merge JSON, recap ghép từ recap cảnh; lỗi 1 cảnh không rớt cả chương | `services/authoring.py` `extract_chapter_facts` |
| A2 | Step `interrupted` (transient) không bị xoá khi resume | Attempts tích luỹ ≥8 → resume → "fail quá 2 lần" tức thì → loop vô hạn ~6 tiếng trên ch14 | `/resume` xoá cả `failed` **và** `interrupted` | `api/routes/authoring.py` |
| A3 | Model trả `timeline_events`/`thread_touches` dạng list **string** | `.get()` trên str → crash `AttributeError` khi ghi extraction | Normalize string→object trước khi ghi (events, states, thread_touches, foreshadow) | `services/authoring.py` |
| A4 | Transient 502/503/504/timeout đánh `failed` → nuốt quota attempts | Run chết trên lỗi mạng tạm thời | Phân loại transient → `interrupted` (không đếm attempts), cap tổng để tránh lặp vô hạn | `services/authoring.py` |
| A5 | Stale `data = parse_json(text)` sau refactor | `NameError` tiềm ẩn | Xoá dòng thừa | `services/authoring.py` |
| A6 | KiraAI cắt cứng **non-stream** ~60s → 504 mọi call sinh văn dài | qwen3.8-flash call ngắn OK (2-47s) nhưng scene_write/facts luôn chết ở 504; đo thử: no-think 61-72s đều 504, **stream:true 200 OK trong 61.2s** (gateway cho SSE sống qua ngưỡng vì bytes chảy liên tục) | Thêm `_complete_streaming` — khi `base_url` chứa `kiraai.vn` thì gửi `stream:true`, gộp `delta.content`, giữ nguyên retry/fail-fast | `ai/providers.py` |
| A7 | `shift_narrative` dời `order_index` chỉ theo desc mọi delta | `DELETE chapter?compact` 500 `UNIQUE constraint failed` khi ≥2 chương cần dời (xoá ch70-73 vượt target — desc cho delta=-1 đẩy ch73→72 đụng ch72) | Hướng dời theo dấu delta: `+1` desc, `-1` asc — slot trống được giải phóng trước mỗi update | `services/repair.py` |

## B. LỖI ĐÃ SỬA (frontend)

| # | Lỗi | Cách sửa | Commit |
|---|---|---|---|
| B1 | Bảng markdown trong chat (~305px) tràn khung panel 282px, cột cuối đè mép card | Wrap `chat-md-wrap` `overflow-x:auto` + siết padding ô để bảng 5 cột vừa khung | `2968223`, `0c670e2` |
| B2 | Panel Trợ lý AI thiếu rail đối xứng bên phải giấy | Thêm rail `CÔNG CỤ` (shell giống rail trái, dock mép phải giấy, chỉ ≥1900px) | `56a25a6` |

## C. KHÓ KHĂN VẬN HÀNH (chưa phải bug — cần quy trình/config)

| # | Vấn đề | Ghi chú |
|---|---|---|
| C1 | Provider `kiraai` hay 504 khi nhiều call cạnh tranh (engine đang viết + ai-fix tay) | Call nhỏ ~2s, call trích ~44-60s; hiện giải quyết bằng retry-loop nền. **Cần**: hàng đợi AI call hoặc giới hạn concurrent trong ModelRouter |
| C2 | `ai_turns.reply_text` cắt 4000 ký tự | Apply bản nháp ai-fix từ reply_text → **mất ~800 ký tự đuôi** (đã gặp thật, phải khôi phục version). **Cần**: lưu full reply hoặc ai-fix trả draft qua channel không cap |
| C3 | DB bị lock khi engine đang viết | Update `target_chapters` trực tiếp phải retry ~phút. **Cần**: endpoint PATCH run-config (không cần restart) hoặc WAL |
| C4 | `pause_after_wave` toggle quá muộn → engine qua sóng không checkpoint | Đã xảy ra arc2→arc3: flag bật sau khi engine đã commit chuyển sóng. **Cần**: cơ chế "tạm dừng mềm" chặn chắn ranh giới |
| C5 | Tìm cảnh theo keyword đơn (`hôn`, `người đàn ông`) → nhiễu | `hôn` khớp cả trong `khôn`, `hồn`. **Cần**: search có word-boundary/semantic cho tiếng Việt |
| C6 | `/summaries/coverage` output lớn | Parse JSON bị vỡ khi helper truncate 4000c — đọc API trực tiếp, không qua in giới hạn |
| C7 | `PATCH /scenes/{sid}` trả 404 | Route đúng cần prefix `/projects/{pid}/scenes/{sid}` — dễ nhầm khi dùng API trực tiếp. Docs/SDK thiếu |
| C8 | ai-fix cảnh bếp phải retry 5 lần mới qua | Provider tranh với engine sóng (đúng C1). Draft 5078c lưu file, apply bằng PATCH — xác nhận luồng "AI nháp → người duyệt → apply" hoạt động khi biết workaround |
| C9 | Update `target_chapters` giữa run phải sửa DB tay | Gặp `database is locked` nhiều lần (engine giữ write lock ~1ph/cảnh), retry mới ghi được. Đã nêu ở mục tiêu #3 |
| C10 | `POST /chapters/{id}/deep-check` đồng bộ quá lâu | Chương 7 cảnh → nhiều call ~45s cạnh tranh engine → vượt client-timeout 280s, không ghi findings. **Cần**: chạy nền như authoring steps + poll status |
| C11 | **Kĩ năng nhân vật không tự kích hoạt** | `Ability` đầy đủ (can_do/cost/counters) nhưng chỉ inject khi ghim tay vào `chapter.cast_json.abilities` — nhân vật cầm kĩ năng xuất hiện mà quên ghim thì kĩ năng "chết"; Ability cũng không gắn chủ nhân (chỉ project-level). **Cần**: link Ability↔Character + auto-suggest ghim khi skeleton nhắc chủ sở hữu (đã vá bằng pilot tự quét, nhưng nên có trong app) |
| C12 | **Hố "phải giải quyết" chưa có cơ chế gọi lại** | `planned_payoff_order` có annotate vào prompt + checker flag "qua cửa sổ payoff", nhưng KHÔNG có bước nào **bắt buộc** dàn payoff trước khi kết — nếu tác giả không tự xử, Hố treo vô thời hạn. **Cần**: bước "resolution sweep" trước hồi cuối — liệt kê Hố quá hạn + bắt outline trả từng cái |
| C13 | Tên cảnh outline trôi khỏi nội dung | Ch23 s0 đặt "Đêm Lakeview" nhưng văn viết ở nhà Hạnh — tên là artefact outline, không ai verify sau khi viết. Sửa tay được; **cần** checker "title vs content" nhẹ |
| C14 | Drift chi tiết qua chương thoát cả 2 checker | Ch17 file ghi "Mục 011 — 24/5", ch25 viết lại thành "15/5" — không canon nào lưu ngày mục đó nên checker không bắt. **Cần**: extraction lưu chi tiết văn bản (ngày/tên/thuộc tính trong trích dẫn) hoặc deep-check soi liên chương |
| C15 | PATCH chapter `cast_json` fail ngầm + format khó đoán | Pilot gửi `cast_json` dạng dict → HTTP 422 (phải là **chuỗi JSON serialized**), và id rút gọn cũng bị chấp nhận lặng/bị reject tuỳ payload — log "đã ghim" nhưng DB `cast_json=None` (không verify sau write). **Cần**: client nhận lỗi rõ + endpoint kiểu `POST /chapters/{id}/cast` chuyên dụng; sau mọi write quan trọng phải đọc lại DB verify |
| C16 | `pause_after_wave` tự reset về 0 | Sau checkpoint sóng 3, field về 0 → sóng kế không dừng → hint không được gieo nếu không canh tay. **Cần**: flag "pause n lần" hoặc pilot tự bật lại mỗi vòng |
| C17 | Extraction tạo thread trùng lặp, không dedupe | ~ch30: 8 thread lặp của motif đã có ("Hai Vạch" vs "Thai ngoài ý muốn/que thử thai", "Quyên và Hà" ×2 chiều, "Mục 019" ×2, "Sợi dây buộc tóc" ×2). Không có cơ chế merge — status là string tự do, set `MERGED` để loại khỏi prompt (`status=="OPEN"`). **Cần**: bước dedupe sau chapter_facts (so title/motif gần giống → gợi ý gộp qua Review Queue) |
| C18 | Signature ảnh trùng giữa 2 nhân vật — ambiguity hay collision? | Ch29 "Hai tấm ảnh" khớp ảnh Mục 001 với hồ sơ Bảo; nhưng canon Khôi cũng mô tả "bàn tay cầm ly cà phê + khung cửa nhìn ra cầu" — trùng signature. Ch41 giải thích ở mức đẹp: cửa sổ phòng Khôi thực sự nhìn ra Cầu Sài Gòn → ảnh là của Khôi chụp nhà mình; mục 019 **được viết sẵn vào file của Linh** bởi tay người khác. Twist có chủ đích, KHÔNG phải collision — nhưng cho thấy canon có thể "chứa sẵn" manh mối mà không checker nào biết nối chúng |
| C19 | Cold restart giữa run: engine tự pause, resume sạch | Tắt backend lúc scene_write đang chạy → run về `paused`, step đánh `interrupted`. Bật lại + POST `/authoring/resume` → tiếp tục đúng scene dở, không mất dữ liệu. Đúng thiết kế resilience; chỉ phiền là `pause_after_wave` lại reset về 0 (xem C16) |
| C20 | Đổi model giữa run (deepseek-v4.1-flash → qwen3.8-flash) | User đưa key mới `kira_…9a94` + yêu cầu Qwen. Đường đúng: `POST /account/credentials` (encrypt Fernet) + UPDATE model_preferences (17 task) + revoke key cũ. Test endpoint OK. **Kết quả**: qwen3.8-flash chết non-stream ở mọi call dài → phải vá bằng A6 (SSE stream) mới viết được; ch68s0 2930c đầu tiên giọng đúng chất file/Mục, nhận đúng trạng thái truyện |
| C21 | `nohup python -m uvicorn` bắt nhầm interpreter | PATH ưu tiên `C:\Python314` (thiếu `aiosqlite`) → backend crash `ModuleNotFoundError` khi khởi động lại. Đúng: `.venv/Scripts/python.exe -m uvicorn` |
| C22 | **Engine không hard-stop ở `target_chapters`** | Đặt 69 nhưng sau khi xong ch69 engine outline tiếp sóng 6 chương (70-75 "Thiệp Không Tên"…) và viết 2 cảnh ch70 trước khi bị pause tay. `target_chapters` chỉ là gợi ý trong prompt dàn khung, không phải điều kiện dừng. Đã xoá 70-75 qua `delete_chapter_full` (phát hiện A7). **Cần**: bước so `chapter_count >= target` → tự mark run done |
| C23 | **Theo dõi "đã trả Hố" không đáng tin** | Kết truyện: 26/41 thread có `planned_payoff_order` không có beat `payoff` nào dù nhiều tuyến đã trả trong prose (Nam ch60, số lạ ch58/68, đám cưới ch63); status thread chỉ OPEN mãi — không gì tự đánh RESOLVED. Extraction tiếp tục sinh trùng (109 OPEN → gộp tay 17, tổng MERGED 25). Dọn tay: 40 RESOLVED đã verify văn, 52 OPEN còn lại gồm micro-thread + ambiguity chủ đích (thai ngoài ý muốn — ô trống tên cha là cái kết không trả lời được, đúng thiết kế truyện) |

## D. PHÁN ĐOÁN TÁC GIẢ — checker flag nhưng GIỮ (false-positive đã verify)

| Finding | Phán đoán |
|---|---|
| KNOWLEDGE_LEAK "Linh biết hôn nhân Bảo sớm" | **False positive** — "cưới người này" là chuyện Nam (người khác), "ảnh cưới cũ" là ảnh profile app. Evidence cần khớp thực thể chặt hơn |
| STYLE_FATIGUE "không ai hỏi" | **Leitmotif chủ đích** — luật khoe của nhóm ("khoe để không ai hỏi thật") |
| STYLE_FATIGUE "ghế thứ năm" | **Motif chủ đích** — đúng tên chương, người thứ năm đã đi |
| STYLE_FATIGUE "chủ đầu tư" | Thuật ngữ nghề của Trang — lặp hợp lý |
| TIME "chín giờ mẹ gọi" lặp nhiều cảnh | **Nghi lễ mỗi tối** ("bà gọi đúng chín giờ mỗi tối"), không phải 1 sự kiện |
| "mười bốn album → à không, đã xóa hết" | Giọng tự-chỉnh chủ đích của nhân vật |
| "bốn người/ba người nữa" đếm | Đếm đúng: Trang đã tới + 3 nữa = 5 ghế |

## E. LỖI TRUYỆN ĐÃ SỬA TAY (author ops — snapshot version hoạt động đúng)

- **Lỗi tên nhân vật**: "Ly" → "Linh" (deep-check bắt được), "ba chữ" vs tin 4 chữ, luật tự phủ định
- **Vai đảo**: "My làm phù dâu" trong khi My là cô dâu → sửa thành My mời Linh làm phù dâu
- **Canon conflicts**: 6 fact trích trùng/đụng (tuổi Linh 33 vs 28, nghề My, việc Trang) → reject bản nhiễu, giữ bản chuẩn đầy đủ nhất
- **Bản nháp ai-fix bị cụt đuôi** (C2) → khôi phục version, apply lại từ response đầy đủ

---

## MỤC TIÊU CẦN SỬA / NÂNG CẤP QUY TRÌNH (backlog ưu tiên)

1. **Hàng đợi AI call** (C1): serialize model calls hoặc semaphore trong ModelRouter — engine sóng và thao tác tay hiện giành provider, gây 504 dây chuyền.
2. **Reply không cap / draft channel** (C2): ai-fix cần trả draft full (bảng riêng hoặc response stream), không dựa `reply_text` 4000c.
3. **PATCH run-config sống** (C3): cho sửa `target_chapters`/`words_per_scene`/`pause_after_wave` không restart, không lock.
4. **Pause-after-wave chắc** (C4): flag phải chặn chắn ranh giới kể cả khi bật giữa sóng cuối — hiện toggle muộn là lỡ sóng.
5. **Search tiếng Việt có dấu** (C5): `func.lower().like()` chỉ fold ASCII; cần unaccent/normalize hoặc FTS5.
6. **Checkpoint trước call lớn**: mọi extraction >~8K chars input tự chia nhỏ (đã làm cho chapter_facts — cần áp pattern cho deep-check, reextract, outline).
7. **Retry/backoff trong engine**: hiện pilot bên ngoài tự resume; nên có retry nội tại với jitter trước khi đánh failed.
8. **UX**: hiển thị `last_error` + nút Resume ngay trên trang authoring khi run failed (hiện user phải biết API).
9. **Giới hạn skeleton độ phình**: hint "Dàn N chương" có thể thổi arc — cần validate tổng chương vs target.
10. **Audit findings có "không phải lỗi"**: đã có REJECTED cho canon; cần trạng thái dismiss cho STYLE_FATIGUE motif chủ đích để checker học không flag lại.
11. **Deep-check async** (C10): đổi sang job nền + endpoint status/poll; hiện call đồng bộ >4ph chắc chắn timeout trên chương dài.
12. **Resolution sweep** (C12): trước hồi cuối, engine nên quét thread OPEN có `planned_payoff_order ≤ current`, liệt kê vào prompt outline — hiện chỉ annotate lẻ tẻ, không có bước thu hồi nợ tập trung.
13. **Ability auto-pin** (C11): gợi ý ghim kĩ năng khi nhân vật sở hữu xuất hiện trong skeleton (liên kết Ability↔Character chưa có — Ability chỉ gắn project, không gắn chủ nhân).

## Quy trình đang vận hành (hoạt động đúng)

- Engine sóng rolling: premise→skeleton→arc outline→scene_write→chapter_facts→checkpoint
- `skeleton` cảnh là lever lái nội dung không đụng prose (đã chứng minh: beat tarot/đũa/dây buộc ăn vào văn)
- Wave hint qua `/approve` lái hướng cả hồi (đã chứng minh: POV Trang, Quyên công khai)
- Snapshot version tự khi PATCH prose; restore version hoạt động
- Deep-check chương bắt lỗi thật (tên nhân vật, vai đảo, drift) với tỉ lệ false-positive cần người lọc
- Pilot tự: resume khi failed, approve+hint khi checkpoint, thêm arc khi cạn skeleton

---

## F. ĐỢT VÁ TRIỂN KHAI (theo 13 mục tiêu trên — đã ship + test)

| # | Mục tiêu | Triển khai | Test |
|---|---|---|---|
| 1 | Hàng đợi AI call (C1) | `ModelRouter._PROVIDER_SEM = Semaphore(2)` — mọi call provider qua 2 slot; retry thêm jitter | `pytest` 162 pass |
| 2 | Reply không cap (C2) | `reply_text` cap 4000→**20000** mọi điểm ghi AiTurn | turn mới có reply đầy đủ |
| 3 | PATCH run-config sống (C3) | `PATCH /authoring/run` — target/words/call_mode/goal_mode/pause_after_wave sửa khi running/paused/awaiting_review, 409 khi run chết | `test_patch_run_config_live` |
| 4 | Pause-after-wave chắc (C4/C16) | Cờ **bền** (không tự reset); đặt được cả `awaiting_review`; `wave_paused_for` chống bắn lặp ranh giới | `test_pause_after_wave_stops_at_boundary` (viết lại cho semantics mới) |
| 5 | Search tiếng Việt (C5) | Regex ranh-từ Unicode `(?<!\w)…(?!\w)` — `hôn` không ăn `khôn/hồn`; LIKE lấy ứng viên rộng → lọc boundary ở Python; ranh chỉ đặt ở phía query là ký tự word (`%`/`100%` vẫn literal) | `test_api_search` 4 pass |
| 6 | — | (đã có: chia window theo provider tier trong deep-check) | — |
| 7 | Retry/backoff nội tại | Jitter `+random(0,3)` trong deep-check calls + provider retry | — |
| 8 | UX error + Resume | AuthoringRoom hiện `last_error` + nút Resume/Approve; panel cấu hình live | tsc sạch |
| 9 | Giới hạn skeleton | `arc_chapters` clamp theo `target_chapters - len(chapters)`; cap số arc dàn thêm | `test_target_chapters_hard_stop` |
| 10 | Dismiss finding | `audit_findings.status` open/dismissed + `dismiss_key`; POST `/dismiss`,`/reopen`; deep-check lọc issue trùng motif đã dismiss | `test_dismiss_reopen_finding_and_filter` |
| 11 | Deep-check async (C10) | Bảng `audit_jobs` + `_spawn_job` (strong-ref chống GC hủy task) + GET `/audit/jobs/{id}`, `/audit/jobs` list; POST trả `job_id` ngay (~0.2s), dedupe 1 job/scope; progress `n/N` ghi vào result_json | `test_deep_check_*`, `test_range_*` viết lại flow poll |
| 12 | Resolution sweep (C12) | Hố OPEN có `planned_payoff_order ≤ target` inject vào prompt `arc_chapters` + `_written_ctx` gần biên target | — (khó test E2E) |
| 13 | Ability auto-inject (C11) | `abilities.owner_character_id` (migration 0028) → compose tự gộp ability của nhân vật có mặt/pinned; block "Năng lực trong chương" | `test_chapter_cast_pins_context` |
| — | Hard-stop target (C22) | Sentinel `__target_done__` — `len(chapters) ≥ target` → complete ngay, không checkpoint rỗng; `next_step` skip outline khi đủ | `test_target_chapters_hard_stop` |
| — | Auto-RESOLVED thread (C23) | Thread có beat `payoff` → status `RESOLVED` tự khi trích facts (verified-prose, không đụng OPEN chủ đích) | — |
| — | Dedupe thread (C17) | Normalize title trước match; tái dùng thread khi title trùng (kể cả khác case/space) | — |
| — | Cast validate (C15) | `PUT /chapters/{id}/cast` — 422 liệt kê id ngoài project, dedupe, trả cast đã lưu; panel đổi endpoint + báo lỗi | `test_chapter_cast_put_validates_ids` |
| — | Latency (C20) | `ai_turns.latency_ms` ghi `time.monotonic` mọi call; `_turn_out` trả field; AiTurnsCard + panel nhật ký hiển thị | — |
| — | Drift checkers (C13/C14) | `TITLE_CONTENT_DRIFT` (tên cảnh nhắc địa danh/thực thể văn không đề cập) + `FACT_DRIFT` (nhãn 'Mục 011' gắn ngày khác nhau giữa chương) trong `/continuity/check` | `/check` trả LOCATION_DRIFT/PHASE_LEAK trên project thật |

## G. BUG MỚI PHÁT HIỆN KHI TRIỂN KHAI (đã vá cùng đợt)

| # | Lỗi | Triệu chứng | Sửa |
|---|---|---|---|
| A8 | `create_task` không giữ ref | Task job nền bị **GC hủy giữa chừng** → row kẹt `running` mãi | `_spawn_job` giữ strong-ref trong `_BG_TASKS` |
| A9 | Connection aiosqlite bind loop | Test per-function loop → pooled conn chết `bound to a different event loop`; + `:memory:` mỗi conn = DB riêng | `pytest.ini` `asyncio_default_*_loop_scope=session`; conftest đổi sang **file DB tạm** |
| A10 | `_dt` chỉ import cục bộ | `_reap_stale_job` dùng `_dt` → NameError nuốt trong `except` → không bao giờ reap | Import `_dt` ở module level |
| A11 | SSE read timeout 600s | Stream câm giữa chừng → `aiter_lines()` treo ~10ph/attempt | `read=120.0` — stall phát hiện sớm → retry được |
| A12 | Job mồ côi chặn dedupe | Process chết giữa job → `running` mãi → POST lại dedupe vào job chết | `_reap_stale_job` (>8ph → failed) ở cả POST lẫn GET list |
| A13 | Compose `pinned_c`/`ranked` undefined | Project 0 nhân vật → NameError trong build context | Khởi tạo mặc định ngoài `if chars:` |

## H. VERIFY CUỐI ĐỢT

- `pytest` **162 pass** (4 test mới: hard-stop, patch config, cast validate, dismiss/reopen, stale reap; 3 test viết lại: pause bền, deep-check job, range job)
- `npx tsc --noEmit` sạch
- Runtime project thật: PATCH run paused↔on/off OK; PUT cast 422 id giả + 200 dedupe; deep-check POST trả job trong 0.2s, poll thấy `1/4`; stale job được đánh failed; `/continuity/check` trả LOCATION_DRIFT mới
- Search `que kem` 3 hits, `hôn` 20 hits (không còn ăn `khôn`), `mục` 69 hits
