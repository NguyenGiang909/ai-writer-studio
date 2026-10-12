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

## 5. Còn lại / hướng tiếp

- **Tauri** (backlog): 1 binary duy nhất thay 3 process — khởi động nhanh, AV ít quét hơn UPX
- UPX=True hiện tại → rủi ro AV false-positive; nếu bị quét, build lại `upx=False`
- Port cố định 8765/3300 — nếu cần, thêm probe port trống vào launcher (hiện báo lỗi rõ)
- Code signing chưa có — Windows SmartScreen sẽ cảnh báo lần đầu
- Zip ship: thêm `Compress-Archive` cuối script khi chốt quy trình
