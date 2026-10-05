# ROADMAP — AI Writer Studio → Story OS

Định vị: **"An IDE for long-form fiction"** — bạn quyết định câu chuyện, AI triển khai câu chữ, hệ thống nhớ mọi thứ.

## Bất biến (không được phá)

- Project là data boundary — mọi entity thuộc project.
- AI không phải Canon authority — generation chỉ là draft/suggestion.
- Suggestion mặc định `pending` — chỉ tác giả duyệt mới materialize.
- `story_time` ≠ `narrative_order` — flashback là hợp lệ.
- Partial disclosure tường minh (`disclosure_level`, `known_aspects`).
- What-if merge chỉ tạo `AuthorDecision` — không tự viết Canon/manuscript.
- Provider secret chỉ server-side; public view chỉ `key_hint`.

## Trục kiến trúc 3 tầng

```
DB TRUTH (StoryState / KnowledgeState / Thread / CanonFact)
    ↓
CONTEXT BUILDER (+ Constraint Manifest)   ← prevent before generation
    ↓
AI (provider-agnostic, BYOK)
    ↓
CONTINUITY CHECKER (deterministic rules)  ← detect after generation
    ↓
AUTHOR (Review queue)
```

AI nằm giữa, không phải nguồn sự thật. Backend giữ: ai chết/sống, ai biết gì,
ai ở đâu, skill gì, hố nào OPEN, canon nào active — tại thời điểm bất kỳ.

## GĐ-α · Nền temporal (điều kiện cho mọi thứ sau)

- [ ] α1 `Scene.story_time` + `narrative_order` + migration + SceneEditor fields
- [ ] α2 Convention `StoryState`: `entity_type` = character/location/item;
      `key` = lifecycle/location/ownership/ability; ghi qua UI nhân vật
- [ ] α3 `services/state.py`: `state_at(entity, story_time)` — state mới nhất ≤ t
- [ ] α4 `KnowledgeState.knower_type="reader"` hỗ trợ từ UI

## GĐ-β · Constraint Manifest (prevent before generation)

- [ ] β1 `services/constraints.py`: `must_respect` / `may_use` / `must_not_invent`
      từ StoryState + Thread OPEN + KnowledgeState theo scene.story_time
- [ ] β2 Inject manifest vào `build_story_prompt` (writing/revision), trước Canon
- [ ] β3 Manifest hiện trong UI — tác giả thấy rõ AI bị ràng gì

## GĐ-γ · Continuity Checker mở rộng (detect after generation)

- [ ] γ1 `DEAD_CHARACTER_APPEARANCE` — reuse extraction F2 để biết ai có mặt;
      ngoại lệ: scene_type flashback/dream/memory
- [ ] γ2 `KNOWLEDGE_LEAK` check theo story_time (fix flashback false-positive)
- [ ] γ3 `STALE_THREAD` narrative debt — warning, không bắt buộc; nhắc khi
      nhân vật liên quan đang có mặt ("dịp reinforce")
- [ ] γ4 `LOCATION_CONFLICT` — char PRISON mà xuất hiện CAPITAL không có event
- [ ] γ5 `ABILITY_NOT_UNLOCKED` — ability unlocked_at > scene.story_time
- [ ] γ6 Check sau `ai/complete` writing → issues đính kèm response

## GĐ-δ · Thread/Intent nghiệp vụ

- [ ] δ1 `ThreadBeat beat_type="considered"` — "Leave pending" ghi dấu
- [ ] δ2 `AuthorDecision.rationale` + `rejected_json` — "tại sao quyết định"
- [ ] δ3 Thread card: `OPEN x chương · last touched Ch71` + Reinforce/Resolve/Pending

## GĐ-ε · What-if + Retcon impact

- [ ] ε1 `impact_preview` đi ngược dependency graph (scene/thread/knowledge/plan)
- [ ] ε2 Branch snapshot; merge → chỉ sinh AuthorDecision
- [ ] ε3 UI so sánh branch A/B

## GĐ-ζ · Sản phẩm hoá

- [ ] ζ1 Auth thật (thay DEV_USER) + audit access-check
- [ ] ζ2 Retrieval thông minh (entity-match) thay "nhét tất cả"; pgvector sau
- [ ] ζ3 Postgres migration khi SQLite đuối
- [ ] ζ4 Tauri desktop packaging
- [ ] ζ5 Architecture Comparison Matrix vs InkWeaver / AI-Novel-Writer /
      AIFictionForge / Sodarie / novel-studio → USE-IDEA/ADAPT/BUILD/SKIP

## Thứ tự thực thi

```
α1 → α3 → β1 → β2 → γ1–γ3 → δ → ε → ζ
      (α2, α4 song song)     (γ4, γ5 khi có data)
```

Cụm lõi α1→β2→γ1-3 khép pipeline: extract → state → constraint → generate → check → review.
