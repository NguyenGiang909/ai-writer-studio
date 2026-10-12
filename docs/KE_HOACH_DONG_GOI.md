# KẾ HOẠCH ĐÓNG GÓI — AI Writer Studio (Windows desktop)

Ngày lập: 2026-10-12 · Rà soát bản `package/` build 2026-10-06

## 1. Kiến trúc đóng gói

```
package/
├── start.bat            launcher: poll /health → mở browser
├── stop.bat             giet writer-api.exe + node web\server.js
├── build_package.ps1    pipeline build tự động (xem §3)
├── build_id.txt         stamp "gitrev-ngay" → /health.build_id
├── node.exe             Node runtime v24.x (x64, ~93MB)
├── writer-api.exe       PyInstaller onefile (backend :8765)
└── web/                 Next.js standalone (frontend :3300)
    ├── server.js        entry: startServer(config bake sẵn)
    ├── node_modules/    deps tối thiểu (traced)
    ├── .next/static/    assets client (COPY TAY — standalone không chứa)
    └── public/          (COPY TAY)
```

- **Backend**: `desktop_main.py` → `ENVIRONMENT=production` → DB + secret.key trong `%LOCALAPPDATA%/AIWriterStudio`; port `WRITER_PORT` mặc định **8765**
- **Frontend**: `NEXT_PUBLIC_API_URL=http://127.0.0.1:8765` **bake lúc build** — đổi port backend phải build lại frontend
- **Upgrade DB**: `ensure_schema()` chạy lúc startup — `create_all` + `ALTER TABLE ADD COLUMN` cho cột thiếu. Quy tắc: **cột mới luôn nullable** (hiện tại đúng — giữ vậy)
- **Provider**: `allow_fake_provider` prod = **False** (dev/test = True) — user chưa cấu hình key nhận lỗi rõ "No AI provider configured", không trả văn giả thầm lặng

## 2. Lỗi đã vá trong đợt rà soát này

| # | Lỗi | Trạng thái |
|---|-----|-----------|
| P0 | `web/.next/` chỉ có `static/` — thiếu `server/`, `BUILD_ID` → `server.js` exit "no production build" ngay lập tức | Đã sửa quy trình copy trong `build_package.ps1` (standalone + static + public đúng chỗ) |
| P0 | `start.bat`: "dong cua so nay de thoat" **sai** — spawn detached, console đóng process vẫn sống → zombie giữ port | Đổi thông báo + thêm `stop.bat` |
| P1 | `allow_fake_provider=True` trong production → user không key nhận văn FakeProvider | config.py: prod default False |
| P1 | Không cách nào đối chiếu phiên bản user chạy | `build_id.txt` stamp + `/health` trả `build_id`/`environment` |
| P2 | Launcher `timeout 3` cố định → cold-start onefile >3s mở trang chết | `start.bat` poll `/health` ≤30s |
| P2 | Không có build script — các bước tay, dễ lệch | `build_package.ps1` 5 bước + smoke test |

## 3. Pipeline build (`build_package.ps1`)

```
[1/5] frontend: NEXT_PUBLIC_API_URL=http://127.0.0.1:8765 npm run build
      → .next/standalone/* → package/web/
      → .next/static       → package/web/.next/static
      → public             → package/web/public
[2/5] backend: .venv pyinstaller writer-api.spec → package/writer-api.exe
[3/5] stamp:  build_id.txt = "gitrev-yyyymmdd-hhmm"
[4/5] verify: chạy node web\server.js :3399 → curl / phải 200
[5/5] gói xong → zip tay hoặc thêm bước Compress-Archive
```

Chạy: `powershell -ExecutionPolicy Bypass -File package\build_package.ps1`

## 4. Checklist trước khi ship

- [ ] `build_package.ps1` chạy sạch (web smoke 200)
- [ ] Máy/profile sạch: `start.bat` → browser mở app được ≤30s
- [ ] `stop.bat` → port 8765/3300 giải phóng (`netstat` trống)
- [ ] `/health` trả `build_id` khớp `build_id.txt`
- [ ] Tạo project mới + lưu + reopen → dữ liệu tại `%LOCALAPPDATA%/AIWriterStudio`
- [ ] Nâng cấp: đặt exe/web mới lên cài cũ, DB cũ mở được (ensure_schema thêm cột)
- [ ] Không key API → gọi AI báo lỗi rõ (không văn giả)
- [ ] Có key → call thật OK; chương/audit/chức năng mới đủ

## 5. Đóng gói D1 — Tauri shell (đã triển khai)

```
package/tauri/
├── tauri.conf.json      productName "AI Writer Studio", id com.aiwriter.studio
├── src/main.rs          shell Rust: spawn sidecar + health poll + tray + cleanup
├── frontend/index.html  splash tối (đợi backend+web sống → navigate :3300)
├── icons/icon.ico       icon app/tray (gen tạm — thay asset thật sau)
├── capabilities/default.json
└── build.rs + Cargo.toml + package.json (@tauri-apps/cli 2.12)
```

**Cách chạy** (`src/main.rs`):
- `spawn_sidecars`: TCP/HTTP probe `127.0.0.1:8765/health` + `127.0.0.1:3300/` — **port đang sống thì tái dùng, không spawn trùng** (crash-kill mở lại vẫn an toàn)
- `find_res`: tìm `writer-api.exe`/`node.exe`/`web/server.js` cạnh exe → `resources/` → `../..` (dev)
- Node spawn kèm `PORT=3300`, `HOSTNAME=127.0.0.1`, `CREATE_NO_WINDOW`
- Splash `index.html` hiển thị ngay; thread nền poll ≤90s → `w.navigate(WEB_URL)`
- Tray icon: **Mở** / **Thoát**; nút X cửa sổ = **ẩn xuống tray** (giữ phiên viết), Thoát mới exit
- `RunEvent::Exit` → `kill_sidecars` giết cả 2 con
- `tauri-plugin-single-instance`: mở lần 2 → focus cửa sổ hiện có

**Build**: `cd package/tauri && npm i && npx tauri build` →
`target/release/bundle/nsis/AI Writer Studio_0.1.0_x64-setup.exe` (~65MB, currentUser — không cần admin) +
`bundle/msi/*.msi` (~82MB). Yêu cầu: Rust stable + MSVC Build Tools + WebView2 (installer tự embed bootstrapper).

**Đã verify**: exe release chạy → 2 sidecar lên :8765/:3300, `/health` trả `build_id` + `environment:"production"`, web 200; kill cứng app → mở lại tái dùng sidecar không trùng; dọn sạch process sau test.

## 6. Còn lại / hướng tiếp

- Icon đang là placeholder gen tự động — cần asset thật (đa-size .ico)
- Sidecar chết khi app **crash** chỉ được dọn nhờ port-probe khi mở lại; bản sau có thể gắn Job Object (KILL_ON_JOB_CLOSE) để OS tự giết con
- UPX=True hiện tại → rủi ro AV false-positive; nếu bị quét, build lại `upx=False`
- Port cố định 8765/3300 — app trả lỗi rõ khi bị chiếm; chưa auto-probe port trống
- Code signing chưa có — SmartScreen cảnh báo lần đầu
- Zip ship bản .bat (phương án A) vẫn giữ: `build_package.ps1` + start/stop.bat
