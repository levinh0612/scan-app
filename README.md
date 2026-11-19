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
Link hiện ở: đầu trang app (mã QR nhỏ, rê chuột để phóng to), tab **Kết nối**, và cửa sổ "ScanApp Cài đặt".

> ⚠️ Link tunnel **công khai, chưa có mật khẩu/PIN**. Chỉ gửi người tin cậy. Thêm PIN nằm trong lộ trình.
> Tắt tunnel: `./run.sh --no-tunnel` (khi đó camera điện thoại chỉ chạy nếu dùng `--https` trong wifi, xem mục 5).

---

## 2. Dùng hằng ngày (người ở tiệm)

| Việc | Làm |
|---|---|
| Mở app | Bấm icon **ScanApp** ngoài Desktop → trình duyệt mở app (server chưa chạy thì tự bật ngầm, chờ vài giây) |
| Lấy QR cho điện thoại | Nhìn **đầu trang** app, hoặc tab **Kết nối** → quét bằng camera điện thoại |
| Quét giấy tờ | Trên điện thoại: tab **Hồ sơ mới** → chụp CCCD, cà vẹt |
| Xem lỗi / link / log | Bấm icon **ScanApp Cài đặt** (cho người cài) |

Trên máy Windows đã chạy `install.cmd`, server tự chạy khi bật máy nên chỉ cần bấm **ScanApp**.

---

## 3. Cài trên macOS (đã thử)

```bash
git clone https://github.com/levinh0612/scan-app.git && cd scan-app
./run.sh                # lần đầu: cài Python/thư viện (vài phút) rồi chạy. Hiện QR + link
./make-mac-app.sh       # tạo 2 icon ngoài Desktop
```

`make-mac-app.sh` tạo (nhận đường dẫn khác làm tham số, vd `/Applications`):

- **ScanApp.app** — bấm đúp: nếu server chưa chạy thì tự bật (qua một cửa sổ Terminal thu nhỏ, tự đóng), rồi mở app trên trình duyệt. Mất khoảng 6–30 giây.
  (macOS không cho app mở từ Finder đọc thư mục `~/Documents`, nên việc khởi động giao cho Terminal.)
- **ScanApp Cài đặt.app** — mở Terminal chạy `./run.sh` (menu, QR + link, log).

Nếu thư mục `scan-app` bị di chuyển, chạy lại `./make-mac-app.sh`. Lần đầu macOS có thể hỏi quyền điều khiển Terminal → chọn OK.
Dừng server: `./stop.sh`. Log: `logs/server.log`, `logs/launcher.log`.

---

## 4. Cài trên Windows 10/11 (chưa thử trên máy thật)

**Chuẩn bị:** Windows 10 bản 1809 trở lên hoặc Windows 11, có internet. Cài **Git** (`winget install --id Git.Git -e`).

```powershell
git clone https://github.com/levinh0612/scan-app.git C:\scan-app
cd C:\scan-app
.\install.cmd          # bấm đúp cũng được; chọn Yes khi Windows hỏi quyền Administrator
```

`install.cmd` (chạy MỘT lần) làm:
1. Kiểm tra phiên bản Windows.
2. Cài môi trường (Python, thư viện, VC++ runtime) và chạy thử.
3. Mở firewall cho cổng (chỉ mạng Private/Domain).
4. Tạo 2 tác vụ chạy ngầm bằng quyền SYSTEM: **ScanApp** (bật máy 30 giây sau là chạy) và **ScanApp-Update**
   (mỗi 30 phút kéo code mới từ GitHub, kiểm tra, restart; bản mới lỗi thì **tự quay về bản cũ**; đang có lệnh in chờ thì hoãn).
5. Tạo 2 icon **ScanApp** và **ScanApp - Cai dat** ở Desktop và Start Menu.

Tuỳ chọn: `.\install.cmd -Port 9000`, `-NoHttps`, `-Token` (dán mã GitHub chỉ-đọc nếu sau này đổi repo sang private).
Gỡ: `.\uninstall.cmd`. Chỉ tạo lại icon: `.\make-shortcut.cmd`.

> `install.ps1` hiện mặc định chạy **https chứng chỉ tự ký trong wifi** (điện thoại phải bấm "Nâng cao → Tiếp tục"),
> chưa dùng tunnel Cloudflare như macOS. Nhiều router chặn điện thoại ↔ máy tính (client isolation) khiến cách này không vào được.
> Việc đồng bộ Windows với tunnel còn trong lộ trình.

**Máy in:** cài driver, đặt khổ giấy mặc định **A5 dọc**; trong hộp thoại in của Chrome/Edge: lề **None**, tỉ lệ **100%**,
tắt **Headers and footers**. Nên đặt IP cố định cho máy tính trong router và tắt Sleep.

---

## 5. Lệnh chạy tay

| Việc | macOS / Linux | Windows |
|---|---|---|
| Cài + cập nhật + chạy (B1→B4) | `./run.sh` | `run.cmd` |
| Bỏ bước pull code | `./run.sh --no-pull` | `run.cmd -NoPull` |
| Chế độ tự động (chỉ restart khi có code mới) | `./run.sh --auto` | `run.cmd -Auto` |
| Tắt / bật tunnel https | `--no-tunnel` / `--tunnel` | `-Tunnel` |
| https tự ký trong wifi (không cần internet) | `--https` | `-Https` |
| Đổi cổng | `PORT=9000 ./run.sh` | `$env:PORT=9000; .\run.cmd` |
| Dừng | `./stop.sh` | `stop.cmd` |
| Chạy không tham số trong cửa sổ lệnh | hiện menu chọn | hiện menu chọn |

Cổng mặc định 8000. Nếu bận (vd Docker) thì **tự chọn cổng trống kế tiếp** (tối đa 30 cổng) và ghi vào `.run/port`.

**4 bước của `run`:**

| Bước | Việc làm |
|---|---|
| **B1. Tài nguyên** | Cài git, Python ≥ 3.10, VC++ runtime (Windows) nếu thiếu; tạo `.venv`; cài thư viện khi `requirements.txt` đổi |
| **B2. Pull** | `git pull --ff-only`; bỏ qua + cảnh báo nếu chưa có remote, có sửa đổi chưa commit, hoặc mất mạng |
| **B3. Kiểm tra** | Biên dịch code, chạy test (nếu có trên máy), thử `import app`. Lỗi → hoàn tác, **không đụng server đang chạy** |
| **B4. Khởi động** | Chưa chạy → start; đang chạy → restart, chờ `/api/health` tối đa 30 giây, không lên thì quay về bản cũ |

---

## 6. Xử lý sự cố

| Triệu chứng | Cách xử lý |
|---|---|
| Điện thoại không mở được link | Dùng link `https://….trycloudflare.com` (QR đầu trang). Link wifi `192.168.x.x` thường bị router chặn (client isolation) |
| Camera trên điện thoại không bật | Camera chỉ chạy trên https. Dùng link tunnel, đừng dùng link `http://` |
| Link tunnel không hiện | Cần `cloudflared` và internet. Xem `logs/tunnel.log`; chạy lại `run` |
| Icon ScanApp báo "chưa chạy được" | Mở **ScanApp Cài đặt** xem lỗi, hoặc `logs/launcher.log` |
| Cổng 8000 bận | Không cần làm gì, app tự chọn cổng khác. Xem cổng thật trong `.run/port` |
| Lỗi thiếu DLL `onnxruntime` (Windows) | Chạy lại `run.cmd` (cài VC++ runtime) |
| `git pull` lỗi đăng nhập | Chỉ xảy ra nếu repo private: chạy `git fetch` một lần để đăng nhập |
| Sau cập nhật server không lên | Script đã tự quay về bản cũ. Báo người phát triển kèm `logs/server.err.log` |
| Ô màu sơn / số loại / số khung sai | Các ô này luôn ở trạng thái "cần soát" vì OCR hay nhầm; so với cà vẹt rồi sửa |

---

## 7. Bảo mật và dữ liệu cá nhân

- Ảnh CCCD là dữ liệu cá nhân (Nghị định 13/2023). App không lưu ảnh, không gọi dịch vụ OCR ngoài. Log mặc định **che nội dung**
  (chỉ ghi dạng ký tự). Bật `SCAN_DEBUG=1` mới ghi chữ gốc, và phải **xoá log sau khi dùng**.
- **Repo public: không commit ảnh giấy tờ, tên, số CCCD, biển số, số khung thật** (kể cả trong code mẫu hay test).
  `.gitignore` chặn `samples/`, `*.jpg`, `*.png`, file `test_*.py`, `benchmark.py`.
- Link tunnel công khai, **chưa có PIN** → không đăng link lên nơi công cộng.
- Tắt lưu ảnh/đồng bộ đám mây của điện thoại nếu không muốn ảnh giấy tờ nằm trong thư viện ảnh.

---

## 8. Cấu trúc

```
scan-app/
├── backend/
│   ├── app.py            # API: /api/scan, /api/peek (xem trước trực tiếp), /api/jobs, /api/links, /api/health
│   ├── validators.py     # kiểm tra CCCD, biển số, số tiền thành chữ
│   ├── jobs.py           # hàng đợi lệnh in (trong RAM)
│   ├── printers.py       # hỏi hệ điều hành về trạng thái máy in
│   ├── qr_print.py       # vẽ QR trong cửa sổ lệnh
│   ├── make_cert.py      # chứng chỉ tự ký cho --https
│   └── selfcheck.py      # bước B3 (cú pháp + test nếu có + import)
├── frontend/index.html   # giao diện: chụp, form, xem trước A5, Lệnh in, Kết nối
├── assets/               # icon (scanapp.png / .ico) + make_icon.py vẽ lại icon
├── run.sh / stop.sh      # macOS/Linux (trong Git Bash tự chuyển sang PowerShell)
├── run.cmd / run.ps1     # Windows: cài + cập nhật + chạy
├── stop.cmd / stop.ps1   # Windows: dừng
├── install.cmd/.ps1      # Windows: cài tự chạy + tự cập nhật + icon (một lần)
├── uninstall.cmd/.ps1    # Windows: gỡ
├── setup-autostart.ps1   # Windows: cách tự chạy đời cũ (đã được install.ps1 thay thế)
├── make-mac-app.sh       # macOS: tạo ScanApp.app + ScanApp Cài đặt.app
├── make-shortcut.cmd/.ps1 + open-app.ps1   # Windows: tạo 2 icon; việc icon ScanApp làm
└── requirements.txt
```

File test và benchmark chỉ có trên máy phát triển, không nằm trong repo.

---

## 9. Giới hạn đã biết

- OCR (RapidOCR) **không có dấu tiếng Việt**: họ tên từ OCR luôn bị đánh dấu vàng. Ưu tiên lấy từ QR.
- QR cà vẹt chỉ cho biển số, không có số khung/số máy → phải OCR (hay nhầm O/0, I/1, B/8, F/P).
- QR CCCD thẻ căn cước mới (2024+) có thể chỉ chứa số định danh.
- Đã chỉnh số khung/số loại theo số máy cho **Honda**; hãng khác phải soát tay.
- Màu sơn đọc chữ khó nên chỉ điền khi mọi chữ đều là tên màu; không thì để trống cho người dùng chọn.
- Ngưỡng "đủ nét" (khung xanh/đỏ) chưa chỉnh trên điện thoại thật.
- "Đã ra giấy" chỉ biết hộp thoại in đã đóng, không biết giấy ra thật.
- Hàng đợi lệnh in nằm trong RAM; restart là mất.
- Link tunnel đổi mỗi lần chạy lại, công khai, chưa có PIN.
- Script Windows chưa kiểm chứng trên máy thật; `install.ps1` chưa dùng tunnel.

## 10. Lộ trình

1. Thêm mã PIN cho link công khai.
2. Đồng bộ Windows với tunnel Cloudflare (tự cài `cloudflared`, bật khi mở máy); thử trên máy Windows thật.
3. Mua máy in, chỉnh vị trí in chồng lên mẫu in sẵn.
4. Đo độ chính xác trên nhiều giấy tờ thật hơn; chỉnh ngưỡng độ nét.
5. Lưu hồ sơ, tìm kiếm, backup.
