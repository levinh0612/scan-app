# ScanApp — quét CCCD + cà vẹt → hợp đồng cầm đồ → in A5

App nội bộ cho tiệm cầm đồ xe máy/ô tô. Điện thoại chụp **CCCD** và **cà vẹt**; máy tính trong tiệm đọc bằng OCR/QR (offline),
tự điền "HỢP ĐỒNG CẦM ĐỒ", đánh dấu ô thiếu/không chắc; người dùng xác nhận rồi mới lưu hồ sơ và in khổ A5.

- Repo: https://github.com/levinh0612/scan-app (**public** → không commit dữ liệu thật, xem mục 10)
- Stack: Python 3.10+ · FastAPI · RapidOCR (onnxruntime) · OpenCV · SQLite · frontend thuần HTML/CSS/JS (không build)
- Ngôn ngữ giao diện, log, comment trong code: **tiếng Việt**

> **Tình trạng thật:** đã chạy thử trên **macOS** (giấy tờ thật, quét bằng iPhone qua link https).
> Script **Windows chưa được chạy thử trên máy Windows nào**. Chưa có máy in thật; toạ độ in chồng lên mẫu in sẵn còn tạm.
> Cà vẹt **ô tô** mới thử bằng dữ liệu giả lập, chưa kiểm chứng trên giấy thật.

**Mục lục:** 1 Chạy app (macOS/Windows) · 2 Dùng hằng ngày · 3 Lệnh chạy tay · 4 Cách hoạt động · 5 Máy in · 6 Dành cho AI agent / dev · 7 Thuật toán OCR · 8 Xử lý sự cố · 9 Giới hạn & lộ trình · 10 Bảo mật

---

## 1. Chạy app (làm MỘT lần)

> **Chỉ cần nhớ 1 file ở thư mục gốc:** Mac → `RUN_THIS_FILE_MACOS.command`, Windows → `RUN_THIS_FILE_WIN.cmd`.
> Các file khác là "ruột" để file đó tự gọi.

### 1.1 macOS (đã thử)

Yêu cầu: macOS có **Git** và **Xcode Command Line Tools** (`xcode-select --install`; thường có sẵn nếu đã có git). Python và thư viện được script tự cài.

```bash
git clone https://github.com/levinh0612/scan-app.git
cd scan-app
./RUN_THIS_FILE_MACOS.command        # hoặc bấm đúp file này trong Finder
```

Việc nó làm: biên dịch `macos/ScanApp.swift` thành `ScanApp.app`, tạo icon **ScanApp** ngoài Desktop rồi mở. Cửa sổ ScanApp tự:
1. **Chưa cài** → cài môi trường (vài phút, có thanh tiến độ).
2. **Chưa chạy** → bật server ngầm.
3. **Sẵn sàng** → hiện **mã QR + link https** cho điện thoại và nút **Mở app trên máy này**. Đóng cửa sổ thì server vẫn chạy ngầm.

Lưu ý: macOS không cho app mở từ Finder đọc `~/Documents`, nên việc cài/chạy giao cho một cửa sổ Terminal thu nhỏ (lần đầu có thể hỏi quyền điều khiển Terminal → OK). Dời thư mục `scan-app` thì bấm lại `RUN_THIS_FILE_MACOS.command`.

Chạy thẳng không cần icon (dev): `./scripts/run.sh` rồi mở `http://localhost:8000`.

### 1.2 Windows 10/11 (chưa thử trên máy thật)

Yêu cầu: **Git for Windows**. Python, VC++ runtime, `cloudflared` được script tự cài.

```bat
git clone https://github.com/levinh0612/scan-app.git C:\scan-app
cd C:\scan-app
RUN_THIS_FILE_WIN.cmd
```

Bấm đúp `RUN_THIS_FILE_WIN.cmd` và chọn **Yes** khi Windows hỏi quyền Administrator. Nó (qua `windows/install.ps1`):
- cài môi trường + `cloudflared` (link https), mở firewall;
- tạo 2 tác vụ ngầm: **ScanApp** (bật máy 30 giây là chạy) và **ScanApp-Update** (30 phút kéo code mới từ GitHub, kiểm tra, restart giữ nguyên link; bản mới lỗi thì tự quay về bản cũ; đang có lệnh in chờ thì hoãn);
- tạo icon **ScanApp** ngoài Desktop (cửa sổ WinForms `windows/open-app.ps1`, cùng 3 trạng thái như Mac).

Tuỳ chọn của `install.ps1`: `-Port 9000`, `-Https` (https tự ký trong wifi thay vì link internet), `-Token` (repo private).
Gỡ: `windows\uninstall.cmd`. Chỉ tạo lại icon: `powershell -File windows\make-shortcut.ps1`.

### 1.3 Linux / Git Bash

`./scripts/run.sh` chạy được trên Linux. Trong Git Bash (Windows), `run.sh` tự chuyển sang `run.ps1`.

### 1.4 Kiểm tra đã chạy

```bash
curl http://localhost:8000/api/health      # trả JSON ok
cat .run/port                               # cổng thật (nếu 8000 bận, app tự chọn cổng khác)
tail -n 50 logs/server.log
```

Điện thoại cần **https** mới bật được camera: dùng link `https://….trycloudflare.com` ở cửa sổ ScanApp / đầu trang app / tab **Kết nối**.

---

## 2. Dùng hằng ngày (người ở tiệm)

| Việc | Làm |
|---|---|
| Mở app | Bấm icon **ScanApp** ngoài Desktop → nút **Mở app trên máy này** (server chưa chạy thì tự bật ngầm, chờ vài giây) |
| Lấy QR cho điện thoại | Cửa sổ ScanApp, hoặc đầu trang app, hoặc tab **Kết nối** → quét bằng camera điện thoại |
| Quét giấy tờ | Trên điện thoại: **Hồ sơ mới** → chụp CCCD, cà vẹt |
| Đặt PIN cho điện thoại | Trên máy tính: **Cài đặt** → đặt PIN 4–6 số (bắt buộc trước khi dùng link công khai) |
| Xem lỗi | `logs/server.log`, `logs/launcher.log`, `logs/install.log` |

Quy trình một hồ sơ:
1. Chụp CCCD / cà vẹt. Khung ngắm **xanh** khi đủ nét, **đỏ** khi chưa nét; kết quả đọc hiện ngay khi ngắm. Khi ảnh nét và các ô chính đọc **giống nhau 3 lần liên tiếp** thì hiện "tự chụp sau 2s" (có nút Huỷ); nút chụp tay luôn dùng được; có đèn flash và lấy nét liên tục nếu máy hỗ trợ.
2. Máy tính điền form. Ô **xanh** = chắc chắn, **vàng** = máy không chắc (soát lại), **đỏ** = thiếu. Dưới ô số máy/số khung/màu sơn/biển số/nhãn hiệu có **ảnh cắt chữ trên thẻ** để đối chiếu.
3. Xem trước hợp đồng A5, bổ sung ô thiếu. Chưa đủ thì **không cho in**. App cảnh báo hồ sơ trùng (biển số, số khung, số máy, CCCD).
4. Lưu hồ sơ → bấm **In** → tab **Lệnh in** (Chờ in / Đang in / Đã gửi máy in / Đã ra giấy / Lỗi, có nút In lại, Huỷ).
5. Sau đó: **gia hạn**, **chuộc**, **thanh lý**, ghi chú; có thống kê, báo cáo, xuất CSV, sao lưu.

Trên máy Windows đã chạy `RUN_THIS_FILE_WIN.cmd`, server tự chạy khi bật máy nên chỉ cần bấm **ScanApp**.

---

## 3. Lệnh chạy tay

| Việc | macOS / Linux | Windows |
|---|---|---|
| Cài + cập nhật + chạy (B1→B4) | `./scripts/run.sh` | `powershell -File scripts\run.ps1` |
| Bỏ bước pull code | `./scripts/run.sh --no-pull` | `powershell -File scripts\run.ps1 -NoPull` |
| Chế độ tự động (chỉ restart khi có code mới) | `./scripts/run.sh --auto` | `powershell -File scripts\run.ps1 -Auto` |
| Tắt / bật tunnel https | `--no-tunnel` / `--tunnel` | `-Tunnel` |
| https tự ký trong wifi (không cần internet) | `--https` | `-Https` |
| Đổi cổng | `PORT=9000 ./scripts/run.sh` | `$env:PORT=9000; powershell -File scripts\run.ps1` |
| Dừng (kể cả tunnel, tiến trình mồ côi) | `./scripts/stop.sh` | `powershell -File scripts\stop.ps1` |
| Chạy không tham số trong cửa sổ lệnh | hiện menu chọn | hiện menu chọn |

Cổng mặc định 8000. Nếu bận (vd Docker) thì **tự chọn cổng trống kế tiếp** (tối đa 30 cổng) và ghi vào `.run/port`.

**4 bước của `run`:**

| Bước | Việc làm |
|---|---|
| **B1. Tài nguyên** | Cài git, Python ≥ 3.10, VC++ runtime (Windows) nếu thiếu; tạo `.venv`; cài thư viện khi `backend/requirements.txt` đổi |
| **B2. Pull** | `git pull --ff-only`; bỏ qua + cảnh báo nếu chưa có remote, có sửa đổi chưa commit, hoặc mất mạng |
| **B3. Kiểm tra** | `backend/selfcheck.py`: biên dịch code, chạy test (nếu có trên máy), thử `import app`. Lỗi → hoàn tác, **không đụng server đang chạy** |
| **B4. Khởi động** | Chưa chạy → start; đang chạy → restart, chờ `/api/health` tối đa 30 giây, không lên thì quay về bản cũ |

**Chạy server thủ công để dev** (không qua script):

```bash
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
cd backend && uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

---

## 4. Cách hoạt động

```
 📱 Điện thoại ──(link https)──▶ 🖥️ Máy tính trong tiệm ──▶ 🖨️ Máy in A5
   chụp, xem, sửa          FastAPI + OCR (offline)        (cắm USB / wifi)
                           SQLite: data/contracts.db
```

**Link cho điện thoại:** camera trình duyệt chỉ chạy trên **https**. Mặc định `run` mở thêm **tunnel Cloudflare** (`scripts/tunnel.sh|ps1`, giữ link sống, tự thử lại 20 giây/lần khi Cloudflare từ chối hoặc rớt; trên Mac/Linux server còn có watchdog tự bật lại tunnel) để có link `https://….trycloudflare.com` (**đổi mỗi lần chạy lại**, không phụ thuộc wifi tiệm). Link này **công khai**, được bảo vệ bằng **PIN** (mục 6.5). Tắt tunnel: `--no-tunnel`; khi đó camera điện thoại chỉ chạy nếu dùng `--https` trong wifi.

**Ảnh giấy tờ:** quét → xử lý trong RAM, không lưu. Chỉ khi **lưu hồ sơ** mới có ảnh nén lưu thành file ở `data/anh/` (xem 6.4).

---

## 5. Máy in

Thêm máy in wifi/USB vào Windows/macOS như bình thường (đặt làm mặc định). ScanApp tự in thẳng khổ **A5**, không hiện hộp thoại,
chỉ in phần điền vào (giấy mẫu in sẵn đặt trong khay). Chạy với mọi máy có driver (phun, laser, máy kim). Trạng thái lấy từ hàng đợi in thật:
Đang in → Đã gửi máy in; hết giấy/mất wifi quá 2 phút → Lỗi + lý do, lệnh bị huỷ để in lại không bị in đôi.

- Vị trí chữ: `backend/template.json` (mm từ góc trên-trái giấy). **Hiện là toạ độ TẠM** đo từ ảnh chụp nghiêng, cần đo lại bằng bản quét chuẩn.
- Xem trước ảnh sẽ in: `GET /api/jobs/<id>/preview.png`; in thử: `/api/print/test.png`.
- Cấu hình `.run/print.json`: `{"printer": "tên", "mode": "driver|escp", "host": "ip", "port": 9100, "dx": 0, "dy": 0}`.
  `dx`/`dy` (mm) bù lệch cơ học; `mode: "escp"` + `host` cho máy kim có card mạng (cổng 9100, **không dấu, chưa thử máy thật**).
- Ảnh in tạm trong thư mục tạm, xoá ngay khi in xong. Biên nhận gia hạn/chuộc/thanh lý cũng in ra A5 (`receipt.py`).
- Nên đặt IP cố định cho máy tính trong router và tắt Sleep.
- Hỏi thông tin máy in trên Windows: `scripts/printer-info.ps1`.

---

## 6. Dành cho AI agent / dev

### 6.1 Quy ước làm việc (đọc trước khi sửa)

- **Ngôn ngữ:** tiếng Việt cho UI, log, comment, commit message. Tên biến/ô dữ liệu theo tiếng Việt không dấu (`ho_ten`, `so_khung`, `bks`).
- **Repo public:** không bao giờ commit ảnh giấy tờ, tên/CCCD/biển số/số khung thật, kể cả trong test hay code mẫu (mục 10).
- **Không commit** `data/`, `.run/`, `logs/`, `.venv/`, `samples/`, ảnh (`*.jpg|png|heic`, trừ `frontend/**/*.png`), `backend/test_*.py`, `backend/benchmark.py`, `backend/bench/` (xem `.gitignore`). Test chỉ nằm trên máy dev nên nhánh sạch có thể không có test.
- **Frontend không có bước build:** sửa file trong `frontend/` là có hiệu lực (server gửi no-cache). Script nạp theo thứ tự trong `frontend/index.html`, mọi thứ ở phạm vi toàn cục, không dùng module.
- **Backend:** router mỏng trong `routes_*.py`, nghiệp vụ nằm ở module riêng (`contracts.py`, `jobs.py`, ...). Module OCR không import `app.py` (tránh import vòng).
- Ghi vào DB hay đổi hành vi in/PIN phải giữ nguyên quy tắc phân quyền ở 6.5.
- Log **mặc định che nội dung**; thêm log mới thì không ghi giá trị thật (chỉ tên ô + trạng thái).
- Sửa script `run.sh` thì sửa cả bản `run.ps1` (hai bản song song, cùng 4 bước B1–B4).
- Thay đổi cấu trúc/API thì cập nhật README này và `docs/`.

### 6.2 Bản đồ mã nguồn

```
scan-app/
├── RUN_THIS_FILE_MACOS.command / RUN_THIS_FILE_WIN.cmd   # điểm vào cho người dùng
├── backend/                  # FastAPI (chạy từ thư mục backend/, module app:app)
│   ├── app.py                # tạo app, /api/scan, /api/peek, /api/stack, /api/links, /api/qr.png, /api/printer, /api/health, /api/shutdown, PWA manifest, watchdog tunnel, vòng sao lưu 6 giờ
│   ├── ocr_parse.py          # RapidOCR + phân tích CCCD/cà vẹt (phần lớn logic OCR) — mục 7
│   ├── multiread.py          # bỏ phiếu nhiều lượt đọc, cắt ảnh đối chiếu
│   ├── stack.py              # gộp nhiều khung hình thành 1 ảnh nét (chọn khung nét nhất + căn ECC)
│   ├── validators.py         # kiểm tra CCCD (mã tỉnh), biển số, số tiền bằng chữ
│   ├── contracts.py          # SQLite: hồ sơ, sự kiện, trùng lặp, gia hạn/chuộc/thanh lý, thống kê, báo cáo, sao lưu/khôi phục
│   ├── routes_contracts.py   # /api/auth/*, /api/settings, /api/contracts/*
│   ├── routes_jobs.py        # /api/jobs/*  (hàng đợi lệnh in)
│   ├── routes_print.py       # /api/print/*  (in thử, in biên nhận)
│   ├── jobs.py               # hàng đợi lệnh in trong RAM (12 giờ, tối đa 30)
│   ├── printing.py           # gửi in: driver hệ điều hành hoặc ESC/P qua TCP 9100
│   ├── printers.py           # hỏi hệ điều hành trạng thái máy in (lpstat / PowerShell)
│   ├── layout.py, render.py, template.json   # dữ liệu hồ sơ → danh sách chữ → ảnh A5 1-bit 300dpi
│   ├── receipt.py            # vẽ biên nhận / bản in thử
│   ├── images.py             # lưu/xoá ảnh giấy tờ theo hợp đồng (data/anh/<mã>/)
│   ├── auth.py               # PIN (PBKDF2), phiên, khoá khi sai nhiều lần
│   ├── settings.py           # cài đặt tiệm (data/settings.json)
│   ├── webutil.py            # kiểm tra "máy chủ hay từ xa", PIN, đọc body, bắt lỗi nghiệp vụ
│   ├── qr_print.py           # vẽ QR trong terminal
│   ├── make_cert.py          # chứng chỉ tự ký cho --https
│   ├── selfcheck.py          # bước B3
│   └── requirements.txt      # rapidocr-onnxruntime, opencv-python-headless, fastapi, uvicorn, python-multipart, pillow, numpy, zxing-cpp, segno, cryptography
├── frontend/
│   ├── index.html            # một trang duy nhất (SPA thuần), nạp css/ và js/
│   ├── css/                  # app-core, app-layout, app-home, app-flow, app-features, app-mobile
│   ├── js/                   # theo chức năng: capture*/scan/peek (chụp+đọc), review*/fields/rules (soát), wizard/phieu-* (phiếu hợp đồng),
│   │                         #   contract-* (danh sách/chi tiết/biểu mẫu), jobs/print*/printer (lệnh in), auth/pin/settings, home/report/help/ui/main
│   └── icons/                # icon PWA
├── scripts/                  # run/stop/tunnel (.sh + .ps1), printer-info.ps1
├── macos/                    # ScanApp.swift + make-mac-app.sh (cửa sổ native trên Mac)
├── windows/                  # install/uninstall/make-shortcut/open-app (.ps1, .cmd)
├── assets/                   # scanapp.png/.ico + make_icon.py
├── docs/                     # bộ tài liệu HTML (mở docs/index.html): nghiệp vụ, ERD, kiến trúc & API, hướng dẫn, vận hành, kiểm thử
├── data/                     # (git-ignore) contracts.db, settings.json, anh/, backup/
├── .run/                     # (git-ignore) port, scheme, server.pid, tunnel.pid, cert, print.json, stopped, no-tunnel
└── logs/                     # (git-ignore) server.log, server.err.log, tunnel.log, launcher.log, install.log
```

### 6.3 API (FastAPI, tự sinh tài liệu tại `/docs`)

**Quét & xem trước** (không lưu gì)

| Method | Đường dẫn | Việc |
|---|---|---|
| POST | `/api/scan` | multipart `cccd_front`, `cccd_back`, `cavet` (đều tuỳ chọn) → `{fields, warnings}`. Mỗi ô: `{value, status: ok|check|missing, note, conf, ...}` |
| POST | `/api/peek` | `kind` = `cavet|cccd_front|cccd_back` + `image` → đọc nhanh 1 khung: `{sharp, glare, qr, fields}` (dùng cho khung ngắm và tự chụp) |
| POST | `/api/stack` | tối đa 10 khung → 1 JPEG đã gộp (header `X-Stack-Used`, `X-Stack-N`) |

**Hợp đồng** (`routes_contracts.py`)

| Method | Đường dẫn | Việc |
|---|---|---|
| POST | `/api/contracts/check` | kiểm tra trùng (biển số, số khung, số máy, CCCD) |
| POST/GET | `/api/contracts` | tạo / liệt kê, tìm kiếm |
| GET | `/api/contracts/stats`, `/report`, `/export.csv` | thống kê, báo cáo theo khoảng ngày, xuất CSV |
| GET | `/api/contracts/{cid}` | chi tiết + sự kiện |
| POST/GET | `/api/contracts/{cid}/anh/{kind}` | tải lên / lấy ảnh giấy tờ |
| POST | `/api/contracts/{cid}/{action}` | `renew`, `chuoc`, `thanh_ly`, `note` (điện thoại có PIN được dùng); `sua`, `huy`, `reopen`, `xoa` (**chỉ máy chủ**; `xoa` phải gửi đúng mã HĐ để xác nhận) |
| GET/POST | `/api/contracts/backups`, `/backup`, `/backup/download`, `/restore`, `/offsite` | sao lưu, tải về, khôi phục, thư mục sao lưu ngoài |

**Lệnh in** (`routes_jobs.py`, `routes_print.py`): `GET/POST /api/jobs`, `GET /api/jobs/{id}/snapshot|preview.png`, `PATCH /api/jobs/{id}`, `POST /api/jobs/{id}/print|cancel`, `DELETE /api/jobs/{id}`; `GET /api/print/test.png`, `POST /api/print/test`, `POST /api/print/receipt(.png)`.

**Hệ thống:** `GET /api/health`, `GET /api/links` (link LAN/https), `GET /api/qr.png`, `GET /api/printer`, `POST /api/shutdown`, `GET /api/auth/status`, `POST /api/auth/login|logout|pin`, `GET/POST /api/settings`.

### 6.4 Dữ liệu và cấu hình

| Thứ | Vị trí | Ghi chú |
|---|---|---|
| Cơ sở dữ liệu | `data/contracts.db` (SQLite, đổi bằng `SCAN_DB`) | bảng `contracts` + `events` (xem dưới) |
| Cài đặt tiệm | `data/settings.json` (`SCAN_SETTINGS`) | mặc định `so_ngay_ky=30`, `le_phi_ky=0`, `anh_giu_ngay=90`, kèm PIN đã băm |
| Ảnh giấy tờ | `data/anh/<mã HĐ>/` (`SCAN_IMAGES`) | cạnh dài ≤ 1280px, JPEG ~70% (~150–250 KB); HĐ đã chuộc/thanh lý/huỷ thì tự xoá sau `anh_giu_ngay` ngày |
| Sao lưu | `data/backup/contracts-YYYYMMDD.db` | mỗi ngày 1 bản, giữ 30 bản; tự chạy nền mỗi 6 giờ và sau thay đổi; có thể chép sang thư mục ngoài (offsite) |
| Cấu hình in | `.run/print.json` | mục 5 |
| Biến môi trường | `PORT`, `SCAN_DB`, `SCAN_SETTINGS`, `SCAN_IMAGES`, `SCAN_DEBUG=1` | `SCAN_DEBUG=1` ghi chữ gốc vào log, chỉ để dò lỗi, phải xoá log sau đó |

- **Mã hợp đồng:** `DDMMYYYY-0000` (ngày tạo + số thứ tự trong ngày, bắt đầu lại từ 0001 mỗi ngày).
- **Trạng thái hợp đồng:** `dang_cam` → `da_chuoc` | `thanh_ly` | `huy` (có `reopen`). Cột `nguon`: `may_tinh` | `dien_thoai`.
- **Bảng `contracts`:** thông tin khách (`ho_ten, cccd, ngay_cap, dia_chi, sdt`), xe (`bks, nhan_hieu, so_loai, so_khung, so_may, mau`), tiền/kỳ (`so_tien, le_phi, so_ngay, tu_ngay, den_ngay`), các cột khoá so khớp đã chuẩn hoá `*_k` (bỏ dấu, chỉ chữ+số, in hoa) và `dedupe` (UNIQUE) để phát hiện trùng.
- **Bảng `events`:** lịch sử gia hạn/chuộc/thanh lý (`type, at, days, amount, den_ngay, note`).
- **Lệnh in** chỉ ở RAM (`jobs.py`), mất khi restart; snapshot chỉ để "In lại".

### 6.5 Phân quyền: máy chủ và từ xa

`webutil._is_local` coi request là **máy chủ** khi đến thẳng, không có header proxy (`cf-connecting-ip`, `x-forwarded-for`, `cf-ray`, `forwarded`). Request qua tunnel là **từ xa** (điện thoại).

- Máy chủ: không cần PIN, được làm mọi thứ (sửa, huỷ, mở lại, xoá hẳn, khôi phục, đặt/đổi PIN, đổi cài đặt).
- Từ xa: phải đăng nhập PIN. PIN 4–6 số, băm PBKDF2. Phiên tự khoá sau **300 giây** không dùng. Sai **5** lần liên tiếp thì khoá mọi lần thử từ xa trong **300 giây**. Đổi PIN → mọi phiên điện thoại bị đăng xuất. Chưa đặt PIN thì không dùng được từ xa.
- Thao tác từ xa được phép trên hợp đồng: tạo, xem, `renew`, `chuoc`, `thanh_ly`, `note`. Phần còn lại chỉ máy chủ.

### 6.6 Kiểm thử và kiểm tra nhanh

- `python backend/selfcheck.py`: biên dịch cú pháp, chạy `test_*.py` nếu có, thử `import app` (đây là bước B3).
- Test (`backend/test_*.py`, pytest/unittest) và `benchmark.py` **không nằm trong repo** (có dữ liệu mẫu giống thật). Nếu cần viết test mới, dùng dữ liệu giả hoàn toàn.
- Hàm thuần dễ kiểm: `validators.py`, `ocr_parse` (parse từ danh sách `Line` giả), `multiread.vote`, `contracts.*` (có tham số `now` để giả lập thời gian, `SCAN_DB` trỏ DB tạm), `layout`/`render`.
- Sau khi sửa: chạy `./scripts/run.sh --no-pull` rồi thử `/api/health` và một lần quét thật trên máy dev.

### 6.7 Việc AI agent hay làm: chỉ dẫn nhanh

| Việc | Sửa ở đâu |
|---|---|
| Đọc sai một ô cà vẹt/CCCD | `backend/ocr_parse.py` (parse theo ô, `KNOWN_MODELS`, `CAVET_RUNS`); bỏ phiếu ở `multiread.py` |
| Thêm ô vào hợp đồng | `contracts.py` (`TEXT_FIELDS`, schema + migrate), `ocr_parse.py`, `backend/template.json`, `layout.py`, `frontend/js/fields.js`, `rules.js`, `phieu-*.js` |
| Đổi vị trí chữ khi in | `backend/template.json` (mm), hoặc `dx/dy` trong `.run/print.json` |
| Thêm API | router mới/hàm trong `routes_*.py`, đăng ký trong `app.py`; dùng `webutil` để kiểm tra máy chủ/PIN |
| Đổi giao diện | `frontend/css/*.css`, `frontend/js/*.js`, `frontend/index.html` |
| Đổi luồng cài đặt/chạy | `scripts/run.sh` **và** `scripts/run.ps1`; `windows/*`, `macos/*` |

---

## 7. Thuật toán OCR

Engine: **RapidOCR** (onnxruntime, offline) + **zxing-cpp** đọc QR. Nguyên tắc: QR chính xác hơn OCR → ưu tiên QR; OCR chạy nhiều lượt rồi bỏ phiếu; ô nào máy không chắc thì đánh `check`/`missing` để người dùng soát.

### 7.1 Đọc cà vẹt (`ocr_parse.read_cavet_multi`)

Một lần OCR hay nhầm (O/0, I/1, B/8…) nên app đọc **nhiều lượt rồi bỏ phiếu**:

1. **Nắn nghiêng:** chạy OCR một lượt để lấy góc nghiêng trung vị của các dòng chữ dài; nghiêng từ 1° đến 25° thì xoay ảnh cho chữ nằm ngang (`ocr_parse.deskew`).
2. **4 lượt đọc**, mỗi lượt xử lý ảnh khác nhau (`CAVET_RUNS`): `clahe` (tăng tương phản), `raw` (ảnh gốc), `up` (phóng 1,5 lần), `flat` (làm phẳng nền).
3. **Bỏ phiếu từng ô** (`multiread.vote`): giá trị được nhiều lượt đọc trùng nhất thắng. Hoà phiếu thì nghiêng về lượt `clahe`, không so độ tin cậy giữa các lượt.
4. **Chốt trạng thái:**
   - Mọi lượt trùng nhau và đúng khuôn dạng → `ok`.
   - Lượt đọc bất đồng → `check` (vàng), kèm giá trị của các lượt khác.
5. **Số loại:** nếu một lượt đọc ra đúng tên xe trong `KNOWN_MODELS` thì chọn tên đó (`pick_known_model`).
6. **Màu sơn:** dòng này hay bị bỏ sót nên có lượt dò riêng vùng ngay dưới dòng "Nhãn hiệu"; lượt nào đọc được nhiều màu hơn thì đúng hơn.
7. **Ảnh đối chiếu:** cắt ảnh nhỏ quanh chữ của từng ô (`multiread.attach_crops`) để người dùng so với giấy thật.

### 7.2 Đọc CCCD (`ocr_parse.parse_cccd`)

Ưu tiên nguồn chính xác nhất, OCR chỉ là phương án dự phòng:

1. **QR trước:** nếu quét được QR thì lấy số CCCD, họ tên (có dấu), địa chỉ, ngày cấp từ QR, trạng thái `ok`. QR lạ định dạng thì cảnh báo và chuyển sang OCR.
2. **Số CCCD:** tìm chuỗi 12 số trong chữ OCR (chấp nhận có khoảng trắng); độ tin cậy ≥ 0,95 mới `ok`. Gặp chữ "CMND" và chuỗi 9 số thì báo đây là giấy loại cũ, yêu cầu khách đưa CCCD/thẻ căn cước.
3. **Họ tên** (khi không có QR): thử dòng MRZ ở mặt sau (`NGUYEN<VAN<AN`), không có thì lấy sau nhãn "Họ và tên". Cả hai đều **không có dấu** nên luôn là `check`, người dùng gõ lại dấu.
4. **Địa chỉ:** lấy các dòng sau nhãn địa chỉ; độ tin cậy dưới 0,97 thì `check` vì địa chỉ dài, dễ sai.
5. **Ngày cấp:** tìm mẫu `dd/mm/yyyy` ở mặt sau rồi mặt trước.

### 7.3 Gộp khung hình (`stack.py`)

Khi chụp có thể gộp tối đa 10 khung liên tiếp: chọn khung nét nhất (phương sai Laplacian) làm gốc, căn các khung còn lại theo nó (ECC), lấy trung bình có trọng số độ nét → giảm nhiễu và chữ mờ do rung tay. Không "bịa" nét chữ (khác AI siêu phân giải).

---

## 8. Xử lý sự cố

| Triệu chứng | Cách xử lý |
|---|---|
| Điện thoại không mở được link | Dùng link `https://….trycloudflare.com` (QR đầu trang). Link wifi `192.168.x.x` thường bị router chặn (client isolation) |
| Camera trên điện thoại không bật | Camera chỉ chạy trên https. Dùng link tunnel, đừng dùng link `http://` |
| Link tunnel không hiện | Cần `cloudflared` và internet. Xem `logs/tunnel.log`; chạy lại `run` |
| Điện thoại đòi PIN / báo khoá | Đặt PIN ở Cài đặt trên máy tính; sai 5 lần thì chờ 5 phút |
| Icon ScanApp báo "chưa chạy được" | Xem `logs/server.log`, `logs/launcher.log` |
| Cổng 8000 bận | Không cần làm gì, app tự chọn cổng khác. Xem cổng thật trong `.run/port` |
| Lỗi thiếu DLL `onnxruntime` (Windows) | Chạy lại `powershell -File scripts\run.ps1` (cài VC++ runtime) |
| `git pull` lỗi đăng nhập | Chỉ xảy ra nếu repo private: chạy `git fetch` một lần để đăng nhập |
| Sau cập nhật server không lên | Script đã tự quay về bản cũ. Báo người phát triển kèm `logs/server.err.log` |
| Ô màu sơn / số loại / số khung sai | Các ô này hay bị OCR nhầm nên thường ở trạng thái "cần soát"; so với cà vẹt (xem ảnh đối chiếu) rồi sửa |
| Máy in không ra giấy / báo Lỗi | Kiểm tra máy in mặc định, hết giấy, wifi; xem tab **Lệnh in** và `/api/printer`; thử in thử `/api/print/test` |
| Server đã chạy nhưng cần dừng hẳn | `./scripts/stop.sh` (Mac/Linux) hoặc `scripts\stop.ps1` (Windows) |

---

## 9. Giới hạn đã biết và lộ trình

**Giới hạn**
- OCR (RapidOCR) **không có dấu tiếng Việt**: họ tên từ OCR luôn bị đánh dấu vàng, ưu tiên lấy từ QR; người dùng tự gõ dấu.
- QR cà vẹt chỉ cho biển số, không có số khung/số máy → phải OCR (hay nhầm O/0, I/1, B/8, F/P).
- QR CCCD thẻ căn cước mới (2024+) có thể chỉ chứa số định danh.
- Đã chỉnh số khung/số loại theo số máy cho **Honda**; hãng khác phải soát tay.
- Màu sơn đọc chữ khó nên chỉ điền khi mọi chữ đều là tên màu; không thì để trống cho người dùng chọn.
- Ngưỡng "đủ nét" (khung xanh/đỏ) chưa chỉnh trên điện thoại thật.
- "Đã ra giấy" chỉ biết hộp thoại in đã đóng, không biết giấy ra thật.
- Hàng đợi lệnh in nằm trong RAM; restart là mất.
- Link tunnel đổi mỗi lần chạy lại và công khai; dữ liệu hợp đồng được bảo vệ bằng PIN.
- Script Windows (kể cả `tunnel.ps1`) chưa kiểm chứng trên máy thật; `install.ps1` chưa bật tunnel khi mở máy.

**Lộ trình**
1. (Đã xong) Mã PIN cho link công khai; lưu hồ sơ, tìm kiếm, sao lưu.
2. Đồng bộ Windows với tunnel Cloudflare (tự cài `cloudflared`, bật khi mở máy); thử trên máy Windows thật.
3. Mua máy in, đo lại toạ độ `template.json` bằng giấy mẫu thật; thử chế độ driver trên Windows và `escp` trên máy kim thật.
4. Đo độ chính xác trên nhiều giấy tờ thật hơn; chỉnh ngưỡng độ nét; kiểm chứng cà vẹt ô tô thật.

Tài liệu đầy đủ (nghiệp vụ, ERD, kiến trúc & API, hướng dẫn, vận hành, kiểm thử): mở `docs/index.html` bằng trình duyệt.

---

## 10. Bảo mật và dữ liệu cá nhân

- Ảnh CCCD là dữ liệu cá nhân (Nghị định 13/2023). App **không gọi dịch vụ OCR ngoài**. Ảnh chỉ xử lý trong RAM khi quét; ảnh của hợp đồng lưu cục bộ trong `data/anh/` và tự xoá sau `anh_giu_ngay` ngày (mặc định 90) khi hợp đồng đã đóng.
- Log mặc định **che nội dung** (chỉ ghi dạng ký tự). Bật `SCAN_DEBUG=1` mới ghi chữ gốc, và phải **xoá log sau khi dùng**.
- **Repo public: không commit ảnh giấy tờ, tên, số CCCD, biển số, số khung thật** (kể cả trong code mẫu hay test). `.gitignore` chặn `samples/`, `uploads/`, `*.jpg`, `*.png` (trừ `frontend/`), `data/`, `*.db`, `test_*.py`, `benchmark.py`.
- Link tunnel công khai: chỉ dùng khi đã đặt PIN; không đăng link lên nơi công cộng.
- Tắt lưu ảnh/đồng bộ đám mây của điện thoại nếu không muốn ảnh giấy tờ nằm trong thư viện ảnh.
