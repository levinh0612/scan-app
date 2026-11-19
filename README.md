# ScanApp — quét CCCD + cà vẹt → hợp đồng cầm đồ → in A5

App nội bộ cho tiệm cầm đồ xe máy/ô tô. Dùng camera điện thoại quét **CCCD** (QR mặt sau / chữ mặt trước) và **cà vẹt**,
app tự điền vào "HỢP ĐỒNG CẦM ĐỒ", đánh dấu ô thiếu/không chắc, người dùng xác nhận rồi mới được in.

- Repo: https://github.com/levinh0612/scan-app (**public**)
- **Đọc giấy tờ offline:** OCR + QR chạy ngay trên máy tính trong tiệm. Ảnh chỉ xử lý trong RAM, **không lưu, không gửi đi đâu**.
- **Chưa lưu hồ sơ.** Hàng đợi lệnh in nằm trong RAM, tắt server là mất.

> **Tình trạng thật:** đã chạy thử trên **macOS** (đọc thử vài giấy tờ thật, quét bằng iPhone qua link https).
> Script **Windows chưa được chạy thử trên máy Windows nào**. Chưa có máy in thật, phần in chồng lên mẫu in sẵn chưa chỉnh.
> Lần cài đầu ở tiệm: làm cùng người phát triển và ghi lại lỗi.

---

## 1. Cách hoạt động

```
 📱 Điện thoại ──(link https)──▶ 🖥️ Máy tính trong tiệm ──▶ 🖨️ Máy in A5
   chụp, xem, sửa          FastAPI + OCR (offline)       (cắm USB vào máy tính)
```

1. Mở app trên điện thoại (quét mã QR) → chụp CCCD / cà vẹt. Khung ngắm **xanh** khi ảnh đủ nét, **đỏ** khi chưa nét.
2. Máy tính đọc, điền form. Ô **xanh** = chắc chắn, **vàng** = máy không chắc (soát lại), **đỏ** = thiếu.
3. Xem trước hợp đồng A5, bổ sung ô thiếu. Chưa đủ thì **không cho in**.
4. Bấm **In** → vào tab **Lệnh in** (Chờ in / Đang in / Đã gửi máy in / Đã ra giấy / Lỗi, có nút In lại).

**Điện thoại vào bằng link nào?** Camera trình duyệt điện thoại chỉ chạy trên **https**. Mặc định `run` mở thêm
**tunnel Cloudflare** để có link `https://….trycloudflare.com` (đổi mỗi lần chạy lại, không phụ thuộc wifi tiệm).
Link hiện ở: đầu trang app (mã QR nhỏ, rê chuột để phóng to), tab **Kết nối**.

> ⚠️ Link tunnel **công khai, chưa có mật khẩu/PIN**. Chỉ gửi người tin cậy. Thêm PIN nằm trong lộ trình.
> Tắt tunnel: `./scripts/run.sh --no-tunnel` (khi đó camera điện thoại chỉ chạy nếu dùng `--https` trong wifi, xem mục 5).

---

## 2. Dùng hằng ngày (người ở tiệm)

| Việc | Làm |
|---|---|
| Mở app | Bấm icon **ScanApp** ngoài Desktop → cửa sổ ScanApp (server chưa chạy thì tự bật ngầm, chờ vài giây) → nút **Mở app trên máy này** |
| Lấy QR cho điện thoại | Ngay trong cửa sổ ScanApp (hoặc đầu trang app, tab **Kết nối**) → quét bằng camera điện thoại |
| Quét giấy tờ | Trên điện thoại: tab **Hồ sơ mới** → chụp CCCD, cà vẹt |
| Xem lỗi / log | `logs/server.log`, `logs/launcher.log`, `logs/install.log` |

Trên máy Windows đã chạy `RUN_THIS_FILE_WIN.cmd`, server tự chạy khi bật máy nên chỉ cần bấm **ScanApp**.

---

## 3. Cài đặt (làm MỘT lần)

> **Chỉ cần nhớ 1 file:** Mac → `macos/RUN_THIS_FILE_MACOS.command`, Windows → `windows/RUN_THIS_FILE_WIN.cmd`. Các file còn lại là "ruột" để file đó tự gọi, không cần mở.

Tải code về (cần Git), rồi **bấm đúp 1 file**:

| Máy | Lấy code | Bấm đúp |
|---|---|---|
| **Mac** (đã thử) | `git clone https://github.com/levinh0612/scan-app.git` | **`macos/RUN_THIS_FILE_MACOS.command`** |
| **Windows 10/11** (chưa thử trên máy thật) | `git clone https://github.com/levinh0612/scan-app.git C:\scan-app` | **`windows\RUN_THIS_FILE_WIN.cmd`** (chọn Yes khi Windows hỏi quyền) |

Xong là có **một icon ScanApp** ngoài Desktop. Bấm vào thì hiện cửa sổ ScanApp:

1. **Chưa cài** → tự cài (vài phút, có thanh tiến độ).
2. **Chưa chạy** → tự bật server ngầm.
3. **Sẵn sàng** → hiện **mã QR + link https** cho điện thoại và nút **Mở app trên máy này**. Đóng cửa sổ thì server vẫn chạy ngầm.

**Mac** — `RUN_THIS_FILE_MACOS.command` chỉ tạo icon (biên dịch cửa sổ Swift, cần Xcode Command Line Tools — đã có sẵn nếu máy có git) rồi mở nó.
macOS không cho app mở từ Finder đọc `~/Documents` nên việc cài/chạy giao cho một cửa sổ Terminal thu nhỏ (lần đầu có thể hỏi quyền điều khiển Terminal → OK).
Dời thư mục `scan-app` thì bấm lại `macos/RUN_THIS_FILE_MACOS.command`.

**Windows** — `RUN_THIS_FILE_WIN.cmd` cài môi trường + cloudflared (link https), mở firewall, tạo 2 tác vụ ngầm: **ScanApp** (bật máy 30 giây là chạy)
và **ScanApp-Update** (30 phút kéo code mới từ GitHub, kiểm tra, restart giữ nguyên link; bản mới lỗi thì tự quay về bản cũ;
đang có lệnh in chờ thì hoãn) cùng icon ScanApp. Nếu bấm icon khi chưa cài, cửa sổ tự chạy cài đặt (Windows hỏi quyền → Yes).
Tuỳ chọn: `-Port 9000`, `-Https` (https tự ký trong wifi thay vì link internet), `-Token` (repo private).
Gỡ: `windows\uninstall.cmd`. Chỉ tạo lại icon: `powershell -File windows\make-shortcut.ps1`.

**Máy in:** cài driver, đặt khổ giấy mặc định **A5 dọc**; trong hộp thoại in của Chrome/Edge: lề **None**, tỉ lệ **100%**,
tắt **Headers and footers**. Nên đặt IP cố định cho máy tính trong router và tắt Sleep.

---

## 4. Lệnh chạy tay

| Việc | macOS / Linux | Windows |
|---|---|---|
| Cài + cập nhật + chạy (B1→B4) | `./scripts/run.sh` | `powershell -File scripts\run.ps1` |
| Bỏ bước pull code | `./scripts/run.sh --no-pull` | `powershell -File scripts\run.ps1 -NoPull` |
| Chế độ tự động (chỉ restart khi có code mới) | `./scripts/run.sh --auto` | `powershell -File scripts\run.ps1 -Auto` |
| Tắt / bật tunnel https | `--no-tunnel` / `--tunnel` | `-Tunnel` |
| https tự ký trong wifi (không cần internet) | `--https` | `-Https` |
| Đổi cổng | `PORT=9000 ./scripts/run.sh` | `$env:PORT=9000; powershell -File scripts\run.ps1` |
| Dừng | `./scripts/stop.sh` | `powershell -File scripts\stop.ps1` |
| Chạy không tham số trong cửa sổ lệnh | hiện menu chọn | hiện menu chọn |

Cổng mặc định 8000. Nếu bận (vd Docker) thì **tự chọn cổng trống kế tiếp** (tối đa 30 cổng) và ghi vào `.run/port`.

**4 bước của `run`:**

| Bước | Việc làm |
|---|---|
| **B1. Tài nguyên** | Cài git, Python ≥ 3.10, VC++ runtime (Windows) nếu thiếu; tạo `.venv`; cài thư viện khi `backend/requirements.txt` đổi |
| **B2. Pull** | `git pull --ff-only`; bỏ qua + cảnh báo nếu chưa có remote, có sửa đổi chưa commit, hoặc mất mạng |
| **B3. Kiểm tra** | Biên dịch code, chạy test (nếu có trên máy), thử `import app`. Lỗi → hoàn tác, **không đụng server đang chạy** |
| **B4. Khởi động** | Chưa chạy → start; đang chạy → restart, chờ `/api/health` tối đa 30 giây, không lên thì quay về bản cũ |

---

## 5. Xử lý sự cố

| Triệu chứng | Cách xử lý |
|---|---|
| Điện thoại không mở được link | Dùng link `https://….trycloudflare.com` (QR đầu trang). Link wifi `192.168.x.x` thường bị router chặn (client isolation) |
| Camera trên điện thoại không bật | Camera chỉ chạy trên https. Dùng link tunnel, đừng dùng link `http://` |
| Link tunnel không hiện | Cần `cloudflared` và internet. Xem `logs/tunnel.log`; chạy lại `run` |
| Icon ScanApp báo "chưa chạy được" | Xem `logs/server.log`, `logs/launcher.log` |
| Cổng 8000 bận | Không cần làm gì, app tự chọn cổng khác. Xem cổng thật trong `.run/port` |
| Lỗi thiếu DLL `onnxruntime` (Windows) | Chạy lại `powershell -File scripts\run.ps1` (cài VC++ runtime) |
| `git pull` lỗi đăng nhập | Chỉ xảy ra nếu repo private: chạy `git fetch` một lần để đăng nhập |
| Sau cập nhật server không lên | Script đã tự quay về bản cũ. Báo người phát triển kèm `logs/server.err.log` |
| Ô màu sơn / số loại / số khung sai | Các ô này luôn ở trạng thái "cần soát" vì OCR hay nhầm; so với cà vẹt rồi sửa |

---

## 6. Bảo mật và dữ liệu cá nhân

- Ảnh CCCD là dữ liệu cá nhân (Nghị định 13/2023). App không lưu ảnh, không gọi dịch vụ OCR ngoài. Log mặc định **che nội dung**
  (chỉ ghi dạng ký tự). Bật `SCAN_DEBUG=1` mới ghi chữ gốc, và phải **xoá log sau khi dùng**.
- **Repo public: không commit ảnh giấy tờ, tên, số CCCD, biển số, số khung thật** (kể cả trong code mẫu hay test).
  `.gitignore` chặn `samples/`, `*.jpg`, `*.png`, file `test_*.py`, `benchmark.py`.
- Link tunnel công khai, **chưa có PIN** → không đăng link lên nơi công cộng.
- Tắt lưu ảnh/đồng bộ đám mây của điện thoại nếu không muốn ảnh giấy tờ nằm trong thư viện ảnh.

---

## 7. Cấu trúc

```
scan-app/
├── backend/
│   ├── app.py            # API: /api/scan, /api/peek (xem trước trực tiếp), /api/jobs, /api/links, /api/health
│   ├── validators.py     # kiểm tra CCCD, biển số, số tiền thành chữ
│   ├── jobs.py           # hàng đợi lệnh in (trong RAM)
│   ├── printers.py       # hỏi hệ điều hành về trạng thái máy in
│   ├── qr_print.py       # vẽ QR trong cửa sổ lệnh
│   ├── make_cert.py      # chứng chỉ tự ký cho --https
│   ├── requirements.txt  # thư viện Python
│   └── selfcheck.py      # bước B3 (cú pháp + test nếu có + import)
├── frontend/index.html   # giao diện: chụp, form, xem trước A5, Lệnh in, Kết nối
├── assets/               # icon (scanapp.png / .ico) + make_icon.py vẽ lại icon
├── scripts/              # "động cơ" chạy server (cài + cập nhật + chạy + dừng)
│   ├── run.sh / stop.sh  # macOS/Linux (trong Git Bash tự chuyển sang PowerShell)
│   ├── run.ps1 / stop.ps1  # Windows
│   └── tunnel.ps1        # Windows: giữ link https sống, tự thử lại khi Cloudflare từ chối/rớt
├── macos/                # icon + cửa sổ ScanApp trên Mac
│   ├── RUN_THIS_FILE_MACOS.command   # bấm đúp: tạo icon ScanApp ra Desktop rồi mở
│   ├── make-mac-app.sh   # biên dịch ScanApp.swift thành ScanApp.app
│   └── ScanApp.swift     # cửa sổ native: tự cài / tự bật server / hiện QR + link
├── windows/              # icon + cửa sổ ScanApp trên Windows
│   ├── RUN_THIS_FILE_WIN.cmd       # bấm đúp: cài tự chạy + tự cập nhật + icon (cần quyền Administrator)
│   ├── install.ps1 / uninstall.cmd / uninstall.ps1
│   ├── make-shortcut.ps1 # tạo lại icon ScanApp
│   └── open-app.ps1      # cửa sổ native (WinForms): tự cài / tự bật / hiện QR + link
└── logs/                 # log chạy máy (không đưa lên git)
```

File test và benchmark chỉ có trên máy phát triển, không nằm trong repo.

---

## 8. Giới hạn đã biết

- OCR (RapidOCR) **không có dấu tiếng Việt**: họ tên từ OCR luôn bị đánh dấu vàng. Ưu tiên lấy từ QR.
- QR cà vẹt chỉ cho biển số, không có số khung/số máy → phải OCR (hay nhầm O/0, I/1, B/8, F/P).
- QR CCCD thẻ căn cước mới (2024+) có thể chỉ chứa số định danh.
- Đã chỉnh số khung/số loại theo số máy cho **Honda**; hãng khác phải soát tay.
- Màu sơn đọc chữ khó nên chỉ điền khi mọi chữ đều là tên màu; không thì để trống cho người dùng chọn.
- Ngưỡng "đủ nét" (khung xanh/đỏ) chưa chỉnh trên điện thoại thật.
- "Đã ra giấy" chỉ biết hộp thoại in đã đóng, không biết giấy ra thật.
- Hàng đợi lệnh in nằm trong RAM; restart là mất.
- Link tunnel đổi mỗi lần chạy lại, công khai, chưa có PIN. Tunnel tự thử lại (20 giây/lần) khi Cloudflare từ chối hoặc rớt.
- Script Windows (kể cả `tunnel.ps1`) chưa kiểm chứng trên máy thật; `install.ps1` chưa bật tunnel khi mở máy.

## 9. Lộ trình

1. Thêm mã PIN cho link công khai.
2. Đồng bộ Windows với tunnel Cloudflare (tự cài `cloudflared`, bật khi mở máy); thử trên máy Windows thật.
3. Mua máy in, chỉnh vị trí in chồng lên mẫu in sẵn.
4. Đo độ chính xác trên nhiều giấy tờ thật hơn; chỉnh ngưỡng độ nét.
5. Lưu hồ sơ, tìm kiếm, backup.
