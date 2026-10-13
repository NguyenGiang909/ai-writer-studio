# TÍCH HỢP VÀO AUTO STORY / WRITER / EDITOR / QC AGENTS

## Dữ liệu theo dự án

```text
projects/<project_id>/
  PROJECT_PROFILE.md
  STORY_BIBLE.md
  STYLE_MEMORY.json
  AUTHOR_FEEDBACK.jsonl
  CONTINUITY_LEDGER.json
  CHAPTER_INDEX.json
  chapters/CH001.md ... CHNNN.md
  qc_reports/CH001_QC.md ... CHNNN_QC.md
  .history/        # các snapshot trước khi ghi, nếu app cho phép
```

Không bao giờ để một `project_id` dùng hồ sơ truyện khác. Skill là logic dùng chung; state tồn tại độc lập.

## Hooks tối thiểu

| Hook | Điều kiện kích hoạt | Công việc | Kết quả |
|---|---|---|---|
| `onAuthorFeedback` | Tác giả khoanh đoạn/nhận xét | Append feedback; học rule confirmed hoặc candidate | Updated style memory + event log |
| `onAuthorRevision` | Tác giả sửa đoạn trực tiếp | Tạo diff → candidate theo phạm vi | Không ghi cứng sở thích khi chưa duyệt |
| `onChapterDraftCompleted(N)` | Writer hoàn tất chương N | QC nội chương + cumulative 1..N | QC report + proposed facts |
| `onChapterApproved(N)` | Tác giả duyệt chương (hoặc bật auto-approve rõ) | Lưu snapshot chapter, commit facts; xác minh hash và audit | Updated index/ledger |
| `onChapterEdited(k)` | Chương cũ đổi nội dung | Invalidate hash/index/facts; re-audit k..latest (và toàn truyện ở lượt close tiếp) | Stale flags + recheck |
| `onCanonChanged` | Thay quy tắc thế giới/nhân vật | Tìm facts và chapters bị ảnh hưởng; invalidate + audit | Impact map + báo cáo |
| `onStyleRuleChanged` | Gu đổi, rule cũ bị phủ định | Tải profile phiên bản mới khi viết; không tự sửa bản đã khóa | New style version |

### Auto pipeline (Writer/Editor/QC)

`Orchestrator.load(project_id) → Writer.draft(N) → Style/Scene QC → CumulativeQC.audit(1..N) → Editor.fix(targeted) → CumulativeQC.reaudit(...) → Author review → commit(approved)`.

Nếu báo `BLOCKER` hoặc `MAJOR` chưa được resolve/override thì không tự `approved`. Tối đa số vòng sửa theo cấu hình (ví dụ 2–3) để tránh lặp vô hạn. Save/checkpoint sau mỗi lần; rollback chỉ khi storage thực sự hỗ trợ.

### Assisted pipeline

`Author selection/edit → suggested fix (diff) → approved changes → feedback and style rule storage → onChapterDraftCompleted if end of chapter`. Không tự thay thế phần khóa.

## Data contract gợi ý

- `project_id`, `chapter_id`, `chapter_revision_hash`, `story_bible_version`, `style_memory_version`, `ledger_version`, `audit_model_version` nên kèm mọi yêu cầu model.
- Báo cáo QC trả JSON hoặc Markdown + JSON machine-readable nếu app cần; `evidence` phải có chapter/scene/source span.
- Dùng optimistic concurrency (`expected_version`) và ghi atomic, tránh 2 agent cùng lúc sửa profile. Có thể dùng hàng đợi duy nhất per `project_id` cho commit.
- Giữ snapshot có thể đảo ngược. Không cho Writer trực tiếp chuyển facts dự đoán thành canon `locked`.
- Với RAG, lưu chunks chương nhưng đừng chỉ dựa vào nearest-neighbor retrieval; mỗi vòng cumulative phải quét **đủ danh sách chương** qua index, và truy raw chunks theo chỗ xung đột.

## Ranh giới công cụ

File `SKILL.md` là chỉ dẫn, không phải chương trình tự kích hoạt webhook hoặc chức năng ghi DB. Trong CLI/IDE/app, hook, file writes và quyền truy cập phải được orchestrator cấp. `tools/novel_state.py` giúp khởi tạo/cất giữ và kiểm tra trạng thái **cấu trúc**, không thể tự phát hiện mâu thuẫn ngữ nghĩa nếu không có Writer/QC LLM thực hiện phân tích.
