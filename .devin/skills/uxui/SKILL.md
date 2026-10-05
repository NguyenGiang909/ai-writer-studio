---
name: uxui
description: UX/UI guidelines for the Story OS writer app — Vietnamese-first, long-form fiction, light/dark themes. Use whenever creating or editing any frontend file (pages, components, globals.css), adding buttons/forms/lists, or when the user mentions giao diện, đẹp, khó dùng, tràn, UX, UI, layout, responsive.
---

# UX/UI — Story OS (writer-first)

App cho người viết tiểu thuyết dài kỳ (vài trăm chương). Ưu tiên: **đọc/viết thoải mái hàng giờ**, **quản lý 300+ chương/100+ nhân vật không tràn**, mọi label đi qua `t(lang, ...)`.

## Quan hệ với các skill design bên ngoài

- **`evon-uiux`** (`.devin/skills/evon-uiux/`, name `ui-ux`) — **bộ quy tắc CHÍNH cho mọi màn app**. Bắt đầu bằng "4 câu hỏi" của nó (mục 0 trong SKILL.md); workflow mặc định = như một designer: brief → 2–3 wireframe → người dùng chọn → dựng. Mở đúng file `references/` khi dựng đúng khối đó (bảng "Mở doc nào khi nào" trong SKILL.md của nó). `references/locked-rules.md` là luật chủ dự án đã chốt — mở trước khi chọn màu/nút.
- **File này** — conventions THẬT của codebase (component nào tồn tại, token nào có, i18n). **Thắng khi mâu thuẫn về fact** ("PostForm có sẵn rồi" > "dựng form theo mẫu skill"); evon-uiux thắng về *cách* dựng (bố cục, token, nhịp, states).
- **`ui-ux-kit`** (`.devin/skills/ui-ux-kit/`) — phụ, dùng cho audit sâu một trang hoặc khi cần khung DESIGN_SYSTEM.md; route §B3/§B2.
- **`design-taste-frontend`** (`.devin/skills/taste-skill/`) — chỉ cho landing/marketing; GSAP/hero không áp dụng. Dial preset app: **VARIANCE 4 · MOTION 3 · DENSITY 6-7**.

## Design tokens (dùng var, không hard-code màu)

```
--ink --ink2   chữ chính/phụ          --paper --paper2  nền app/nền phụ
--panel        nền card               --line            viền, divider
--muted        chữ mờ, meta           --gold --gold2    accent nhấn, thương hiệu
--teal         accent hành động, drag indicator
--red          nguy hiểm/xoá           --shadow          đổ bóng card
```

- Theme sáng/tối qua `html[data-theme="dark"]` — mọi CSS mới phải check cả hai; màu hard-code chỉ khi thật sự cần và phải có variant dark.
- Không tạo màu mới nếu token hiện có dùng được.

## Reuse trước khi viết mới (components/)

| Cần | Dùng | Không |
|---|---|---|
| Form thêm/sửa | `PostForm` (`method="post"`, `method="patch"`; `triggerClass`, `triggerLabel`; field `type:"select"|"textarea"|"number"`, `defaultValue`, `required`) | Viết `<form>` thủ công |
| Nút hành động nhanh | `ActionButton` (`method`, `body`, `confirm`) | Fetch thủ công |
| Lọc list dài | `ListFilter` (`for=id`, rows có `data-q`, nhóm có `data-group`) | Tự viết filter |
| Điều hướng | `LeftNav`/`NavLink` | Link tự viết |
| Kéo-thả sắp xếp | class `.sort-row` + `draggable` + `data-drag-id` trong `[data-sort-list]` có `[data-bucket]`; handler sẵn trong `AppBehaviors` | HTML5 drag tự viết |

CSS class có sẵn (xem `app/globals.css` trước khi thêm rule): `.card .btn .ghost .primary .sm .person .list-row .section-label .subtle .badge .chip .avatar .list-filter .drag-handle .tree-* .chapter-* .scene-* .dash-* .editor-* .chat-*`.

## Quy tắc layout

1. **Trang dữ liệu** = `main.main > .dashboard > .dash-head + .grid > .card`. `dash-head` chứa `.eyebrow` + `<h1>` + action chính (`＋` PostForm, `btn primary`).
2. **Hành động trên row**: thứ tự cố định `↑↓(move) → Sửa(ghost sm) → ✕(delete)`. Nút xoá luôn `confirm` kèm tên đối tượng và hậu quả ("Bí danh/arc/quan hệ đi theo.").
3. **List dài**: bắt buộc `ListFilter` ở header card; nhóm theo `data-group` + `h4.section-label` có số lượng; row có `data-q` đủ từ khoá.
4. **Empty state**: `p.subtle` nói rõ "Chưa có X nào." — không để card trắng.
5. **Meta/phụ**: `.subtle`/`<small>` với `--muted`; không nhỏ hơn ~10.5px.
6. **Density**: list quản lý (nhân vật, quan hệ) padding ~8–15px/row; đừng làm card con lồng card con.

## Interaction

- Mọi mutation xong phải có feedback: `toast()` (xem `AppBehaviors`), `SaveIndicator`, hoặc `router.refresh()` — không silent update.
- Trạng thái đang tải/đã lưu dùng `SaveIndicator`; form submit có disable trong `PostForm` sẵn — đừng phá.
- Kéo-thả: `.dragging{opacity:.45}`, `.drag-over{box-shadow:inset 0 2px 0 var(--teal)}`, tay cầm `.drag-handle` (`⋮⋮`, `cursor:grab`).
- Collapse nhóm: toggle `aria-expanded` + class `.collapsed`; khi đang filter (`ListFilter`/tìm chương) thì force mở để kết quả hiện.
- `Esc` đóng drawer/panel; `.menu-toggle`/`.ai-toggle` cho mobile (đã có trong `AppBehaviors`).

## Responsive (breakpoint ~760px)

- `.left`/`.right` panels thành drawer qua `.open`; nav-item click trên mobile đóng drawer.
- Grid `dashboard` phải xuống 1 cột; form modal không rộng quá viewport; nút row-level không nhỏ hơn ~28px hit-area.

## i18n

- Mọi chữ hiển thị: `t(lang, "Tiếng Việt")` + key EN trong `lib/i18n.ts` **không trùng key** (file đã từng lỗi TS1117).
- `t()` hỗ trợ `{name}`, `{n}` interpolation — dùng thay vì nối chuỗi.

## Checklist trước khi xong 1 trang/component

- [ ] Token CSS, không màu cứng; dark theme không vỡ
- [ ] List có lọc + nhóm + empty state nếu có thể >20 items
- [ ] Xoá có confirm nêu hậu quả; sửa đổ `defaultValue` dữ liệu cũ
- [ ] Chữ đi qua `t()` + có key EN; không duplicate key trong i18n.ts
- [ ] `tsc --noEmit` sạch
- [ ] Mobile: không tràn ngang, drawer đóng được
