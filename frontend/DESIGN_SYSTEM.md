# DESIGN_SYSTEM.md — Story OS Writer

Nguồn chân lý visual cho app. Mọi trang/component mới dùng đúng giá trị ở đây; đổi gì thì sửa file này trước.

## 1. Surface profile & concept

- **Profile:** App / Product UI (ui-ux-kit §B3) + Dashboard/Data (§B2) cho trang quản lý dày.
- **Concept:** *"Sổ tay của editor"* — mật độ cao, chữ serif editorial cho tên/tiêu đề, sans gọn cho meta, hành động chỉ lộ khi cần, màu chỉ nói khi có nghĩa.
- **Dial preset (taste-skill):** VARIANCE 4 · MOTION 3 · DENSITY 6-7.

## 2. Color (tokens — `app/globals.css`)

Live theme = **cool gray editorial** (`:root` thứ hai — block "Apple-inspired"). Light/dark qua `html[data-theme="dark"]`, **không đảo màu thủ công** — chỉ đổi token.

| Token | Light | Dark | Vai trò |
|---|---|---|---|
| `--ink` | `#34363a` | `#e8e6e1` | chữ chính |
| `--ink2` | `#47494d` | `#d8d6d0` | chữ phụ, heading phụ |
| `--muted` | `#63666b` | `#aaa8a2` | meta text (đã nâng cho AA) |
| `--paper` | `#e8e9eb` | `#242526` | nền app |
| `--paper2` | `#dcdee1` | `#303133` | nền phụ, pill trung tính |
| `--panel` | `#f1f2f3` | `#2b2c2e` | card |
| `--line` | `#c9ccd0` | `#454648` | viền, divider |
| `--teal` | `#39786f` | `#65b7aa` | accent hành động, active, tier-0 |
| `--gold` | `#806b45` | `#d0ad70` | accent nhấn (eyebrow) |
| `--red` | `#b95c55` | `#e77970` | nguy hiểm/xoá |
| `--shadow` | `0 18px 48px rgba(42,45,50,.08)` | `0 18px 48px rgba(0,0,0,.28)` | đổ bóng card |

- Chiến lược: **Restrained** — neutral xám + teal làm accent duy nhất ≤10%.
- Contrast đã tính (WCAG AA ≥4.5 body): ink/panel **10.80L / 11.21D**, muted/panel **5.14L / 5.88D**, teal/panel **4.58L / 5.93D**, ink2/paper2 **6.69L / 8.96D**.
- **Debt:** theme giấy ấm (`:root` đầu) đã chết nhưng sót hex ấm: `.notice #f5ead3`, `.draft-card #fffdf7`, `.field input white`, `.review-item white` — cần token hoá khi chạm tới.

## 3. Typography

- **Body/UI:** `"Be Vietnam Pro", "Segoe UI", ui-sans-serif` — chọn vì Việt-native đầy đủ dấu.
- **Display/tên:** `'Noto Serif', Georgia, serif` — h1, card h3, avatar initials, tên entity.
- **Mono:** `Cascadia Mono, Consolas` — eyebrow, chỉ số kỹ thuật.
- Scale: h1 `30-32px` serif 700 · h3 card `17-18px` serif 700 · body `15px/1.5` (quyết định density cho product UI — phe miễn trừ có chủ đích khỏi rule 16px) · meta/small `12-14px` · section label `11px` uppercase tracked.
- `letter-spacing:-0.01em` trên body.

## 4. Spacing, radius, elevation

- Radius scale: `7-9px` input/chip nhỏ · `8px` nút (pill `999px` trong theme mới) · `12px` card · `99px` pill/badge.
- Density row quản lý: `.person` pad `11-15px 0`, `.list-row` `8-12px 0`, chia bằng `border-top:1px solid var(--line)`.
- Elevation: tách bằng **nền + shadow**, card `border:1px solid var(--line)` cho phép trong dense UI. Không card-lồng-card.
- Tách nhóm: pill header (`h4.imp-h`), không đường kẻ nặng.

## 5. Components (tái dùng bắt buộc)

| Thành phần | Class / component |
|---|---|
| Nút | `.btn` · `.btn.primary` · `.btn.ghost` · `.btn.sm` · `.btn.gold`; ActionButton (fetch), PostForm (form) |
| Row entity | `.person` (avatar + person-main + row-actions) · `.list-row` · `.sort-row` + `.drag-handle` |
| Nhóm list | `h4.imp-h[data-tier=0..3]` (teal→neutral→dashed) · `[data-group]` + ListFilter `data-q` |
| Feedback | `#toast` + `.toast.show` · `.err` · `.subtle` · `.badge`/`.chip`/`.pill` |
| Form | `.postform .field label+input/textarea/select` — PostForm hỗ trợ patch + defaultValue |
| Filter | `.list-filter` |

## 6. States (bắt buộc đủ bộ)

- Interactive: hover · `:focus-visible` ring `2px var(--teal)` offset 2 · `.btn:active{scale(.97)}` · disabled.
- `.row-actions{opacity:.28}` → `1` khi hover/focus-within row (progressive disclosure, không display:none — tránh layout shift).
- Drag: `.dragging{opacity:.45}` · `.drag-over{inset 0 2px 0 var(--teal)}` · `.drag-handle` ⋮⋮ grab.
- Data view: empty (`p.subtle` "Chưa có X."), loading (`SaveIndicator`/`…`), error (`.err`/toast).
- Delete luôn `confirm` nêu tên + hậu quả.

## 7. Motion

- Chỉ `transform`/`opacity`, ~120-250ms, ease mặc định; `.btn:hover` translateY(-1px).
- `@media (prefers-reduced-motion:reduce)` tắt transition trên `.row-actions`/`.btn`.

## 8. Icons

- Không thư viện icon — dùng ký tự unicode nhẹ (`⋮⋮` `↑` `↓` `✕` `＋` `▾` `▸` `⌄` `›` `☀` `◐`). Giữ vậy cho nhất quán; nếu thêm icon lib thì chọn **một** (gợi ý Phosphor) rồi thay hết.

## 9. i18n & content

- `t(lang,"Tiếng Việt")` + key EN trong `lib/i18n.ts` — không trùng key. `{name}`/`{n}` interpolation.
- Microcopy: empty state nói hành động tiếp theo; confirm xoá nêu hậu quả cascade.

## 10. Layout & responsive

- Trang dữ liệu: `main.main > .dashboard > .dash-head + .grid(auto-fit,minmax(340px,1fr)) > .card`.
- `dashboard` max-width `1250px` căn giữa.
- Mobile <760-1180px: `.left`/`.right` thành drawer (`.open`, Esc đóng), nav-item click đóng drawer; không tràn ngang.

## 11. Accessibility floor

- Semantics thật (`button`, `a`, `nav`, `main`); `aria-expanded` trên collapse; `aria-label` trên icon-only.
- `:focus-visible` toàn cục (xem §6); không `outline:none`.
- Màu không mang nghĩa một mình: status có label text, tier pill có chữ.

## 12. Pre-flight gate (đã chạy trên trang Nhân vật)

- [x] Không màu ngoài palette mới thêm; hex cũ sót lại đã token hoá trên path trang này.
- [x] Contrast AA: pass (số ở §2) — đã sửa `--muted` light `#73767b`→`#63666b` (4.07→5.14).
- [x] Không static interactive — hover/focus/active đủ; delete có confirm.
- [x] Không card-lồng-card, không gradient, không icon emoji làm structural icon.
- [x] `tsc --noEmit` sạch; trang render 200.
- [-] Render-verify 375/768/1280: chưa chụp — built-to-target, **chưa xác nhận trực quan**.

## 13. Component debt / known gaps

- Warm-hex sót lại ở `.notice`, `.draft-card`, `.review-item`, `.field input` (§2 debt).
- `.section-label` cũ vẫn dùng ở trang khác — khi chạm trang đó, đổi sang `h4.imp-h` hoặc giữ `.section-label` cho header chung (không phải tier).
- Scene kéo-thả chưa có (chỉ chapter + entity lists).
- Body 15px là exception density có chủ đích — khi tăng, tăng cả list-filter/meta cho đồng nhất.

## 14. Quy trình khi redesign trang khác

1. Đọc skill `ui-ux-kit` → route §B3 (hoặc §B2 nếu trang data-dense) → Design Read 1 dòng.
2. Audit 1d trước khi sửa; sửa tối thiểu hiệu quả nhất.
3. Contrast tính bằng công thức (không đoán) cho mọi cặp chữ/nền mới.
4. `tsc` + render check + cập nhật file này ngay.
