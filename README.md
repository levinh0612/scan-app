# Scan cà vẹt + CCCD → in hợp đồng cầm đồ (A5)

App nội bộ cho tiệm cầm đồ: chụp CCCD và cà vẹt bằng điện thoại, tự điền vào hợp đồng, xem trước,
bổ sung ô thiếu rồi in ra giấy A5.

- Repo: https://github.com/levinh0612/scan-app
- **Offline hoàn toàn:** OCR chạy trên máy trong tiệm, ảnh chỉ xử lý trong RAM, **không ghi đĩa, không gửi ra internet**.
- **Chưa lưu hồ sơ** (để giai đoạn sau).

> **Trạng thái:** giao diện, backend, bộ kiểm tra dữ liệu (5 test đạt) và script cài/chạy đã viết xong.
> **Chưa chạy thử OCR trên ảnh thật, và script Windows (`.ps1`) chưa được chạy thử trên máy Windows nào.**
> Lần cài đầu tiên ở tiệm hãy làm cùng người phát triển và ghi lại lỗi nếu có.

---

## 1. Mô hình

```
 ┌──────────────┐   wifi   ┌─────────────────────────────┐   USB/LAN   ┌────────────┐
 │ 📱 Điện thoại│ ───────▶ │ 🖥️ Máy tính Windows trong tiệm│ ──────────▶ │ 🖨️ Máy in  │
 │ chụp giấy tờ │ ◀─────── │  FastAPI + OCR (offline)    │             │   A5       │
 │ xem/sửa form │  dữ liệu │  trang web xem trước + In   │             │ (giấy than)│
 └──────────────┘          └─────────────────────────────┘             └────────────┘
        ▲  chỉ trong mạng nội bộ. Không mở port ra internet.
              GitHub ──(máy tiệm tự kéo code mỗi 5 phút)──▶ Máy tính
```

Một hồ sơ: điện thoại chụp → máy tính đọc → xem preview, nhập ô đỏ → bấm **In** trên máy tính
→ hộp thoại "Hoàn thành hồ sơ xe … và chủ xe …".

In từ máy tính vì driver máy in cài trên máy đó; máy in kim hầu hết không có wifi nên cắm USB.
Muốn bấm In ngay trên điện thoại thì cần in phía server (xem "Lộ trình").

## 2. Script

| Việc | Windows | macOS / Linux |
|---|---|---|
| Cài + cập nhật + chạy (B1→B4) | `run.cmd` (bấm đúp được) | `./run.sh` |
| Bỏ bước pull code | `run.cmd -NoPull` | `./run.sh --no-pull` |
| Chế độ tự động (chỉ restart khi có code mới) | `run.cmd -Auto` | `./run.sh --auto` |
| Dừng | `stop.cmd` | `./stop.sh` |
| **Icon ngoài màn hình**: `ScanApp` (bấm = mở app, tự bật server ngầm) + `ScanApp Cài đặt` (cửa sổ QR + link + log) | `make-shortcut.cmd` (`install.cmd` tự tạo) | `./make-mac-app.sh` → 2 app ngoài Desktop |
| Bật tự chạy + tự cập nhật | `setup-autostart.ps1` (Windows) | cron/launchd (tự đặt: gọi `./run.sh --auto`) |

`run.sh` tự nhận OS: chạy trong Git Bash trên Windows thì tự chuyển sang `run.ps1`.

**4 bước của `run`:**

| Bước | Việc làm |
|---|---|
| **B1. Tài nguyên** | Cài **git**, **VC++ runtime**, **Python ≥ 3.10** nếu thiếu (Windows: `winget`; macOS: `brew`; Linux: `apt/dnf`). Tạo `.venv`. Cài thư viện (chỉ khi `requirements.txt` đổi). Mở firewall cổng 8000 (Windows, cần quyền Admin). |
| **B2. Pull** | `git pull --ff-only`. Bỏ qua + cảnh báo nếu chưa có remote, có sửa đổi chưa commit, hoặc mất mạng. |
| **B3. Kiểm tra** | Biên dịch code, chạy test, thử `import app`. Lỗi → hoàn tác code, **server đang chạy không bị đụng tới**. |
| **B4. Khởi động** | Chưa chạy → start. Đang chạy → restart. Chờ `/api/health` tối đa 30 giây; không lên thì quay về bản cũ và chạy lại. |

Chạy lại bao nhiêu lần cũng an toàn.

---

## 3. LẦN ĐẦU — cài trên máy Windows trắng bóc

**Chuẩn bị (5 phút):**
- Windows 10 (bản 21H1 trở lên) hoặc Windows 11, đã cập nhật, có internet.
- Máy tính và điện thoại **cùng một mạng wifi**.
- Đặt wifi đó là **Private**: *Settings → Network & Internet → Wi-Fi → (tên wifi) → Network profile type → Private*.
  (Để Public thì Windows chặn điện thoại vào.)
- (Repo đang public nên máy tiệm tải code không cần đăng nhập GitHub; nếu sau này đổi private thì cần tài khoản có quyền vào repo.)

**Các bước:**

1. **Mở PowerShell bằng quyền Administrator** (Start → gõ `PowerShell` → chuột phải → *Run as administrator*).
   Chỉ lần đầu cần Admin (để mở firewall).
2. **Cài Git** (nếu máy chưa có):
   ```powershell
   winget install --id Git.Git -e
   ```
   Xong **đóng cửa sổ PowerShell và mở lại (vẫn bằng Admin)**. Nếu máy báo không có `winget`, tải Git tại https://git-scm.com/download/win.
3. **Tải code về:**
   ```powershell
   git clone https://github.com/levinh0612/scan-app.git C:\scan-app
   ```
   Nếu repo là private, cửa sổ đăng nhập GitHub sẽ hiện ra → đăng nhập một lần, Windows nhớ cho các lần sau
   (cần cho việc tự cập nhật).
4. **Chạy cài đặt + khởi động:**
   ```powershell
   cd C:\scan-app
   .\run.cmd
   ```
   Script tự cài Python 3.13, VC++ runtime, các thư viện (**5–15 phút**, tùy mạng), mở firewall, kiểm tra, rồi start.
   Cuối cùng in ra:
   ```
   Máy này     : http://localhost:8000
   Điện thoại  : http://192.168.x.x:8000
   ```
5. **Thử trên điện thoại:** mở địa chỉ "Điện thoại" bằng Safari/Chrome → *Thêm vào Màn hình chính*.
6. **Cài máy in:** cài driver, đặt khổ giấy mặc định **A5 dọc**. Trong hộp thoại in của Chrome/Edge:
   lề **None**, tỉ lệ **100%**, tắt **Headers and footers**.
7. **Bật tự chạy + tự cập nhật** (cũng trong PowerShell):
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup-autostart.ps1
   ```
   Từ giờ: bật máy → app tự chạy; cứ 5 phút kiểm tra GitHub có bản mới không.
   Nên bật **tự đăng nhập Windows** trên máy tiệm (tác vụ chỉ chạy khi đã đăng nhập) và **tắt Sleep**.
8. **Đặt IP cố định** cho máy tính trong router (DHCP reservation) để địa chỉ trên điện thoại không đổi.
9. **Kiểm thử bằng giấy tờ thật** (xem mục 6) trước khi dùng thật.

## 4. CÁC LẦN TIẾP THEO

**Dùng hằng ngày:** bật máy tính (đã bật tự chạy ở bước 7) → mở icon trên điện thoại → chụp → kiểm tra → in.
Không cần mở gì trên máy tính ngoài trang web để bấm In.

**Cập nhật phiên bản mới:**
- Người phát triển `git push` lên nhánh `main`.
- Trong tối đa 5 phút, máy tiệm tự kéo code, kiểm tra, restart. Nếu bản mới lỗi → **tự quay về bản cũ**.
- Muốn cập nhật ngay: bấm đúp `run.cmd`.

**Việc thường gặp:**

| Cần làm | Lệnh (Windows, trong `C:\scan-app`) |
|---|---|
| Khởi động lại / cập nhật ngay | `.\run.cmd` |
| Dừng server | `.\stop.cmd` |
| Xem log | `Get-Content logs\server.err.log -Tail 50` |
| Gỡ tự chạy | `powershell -ExecutionPolicy Bypass -File .\setup-autostart.ps1 -Remove` |
| Đổi cổng | `$env:PORT=9000; .\run.cmd` |

**Nếu có sự cố:**

| Triệu chứng | Cách xử lý |
|---|---|
| Điện thoại không vào được | Cùng wifi chưa? Wifi đặt **Private** chưa? Đã chạy `run.cmd` bằng Admin một lần để mở firewall chưa? Router có bật "AP isolation/Client isolation" không (tắt đi). |
| `Cổng 8000 đang bị chương trình khác dùng` | `.\stop.cmd`, hoặc đổi cổng như bảng trên. |
| Lỗi thiếu DLL khi `import onnxruntime` | Chạy lại `.\run.cmd` (sẽ cài VC++ runtime), hoặc cài tay *Microsoft Visual C++ Redistributable 2015-2022 x64*. |
| Cài thư viện rất lâu / lỗi mạng | Thử mạng khác (phát 4G), chạy lại `.\run.cmd` (phần đã tải được giữ lại). |
| `winget` không có | Cài tay Git và Python 3.13 (nhớ tick "Add Python to PATH"), rồi chạy lại. |
| `git pull` báo lỗi đăng nhập | Chạy `git fetch` trong thư mục một lần để Windows hỏi lại đăng nhập GitHub. |
| Sau cập nhật server không lên | Script đã tự quay về bản cũ. Báo người phát triển kèm `logs\server.err.log`. |

### macOS / Linux
```bash
git clone https://github.com/levinh0612/scan-app.git && cd scan-app
./run.sh            # lần đầu: cài mọi thứ + chạy. Lần sau: pull + kiểm tra + restart
./stop.sh
```
Tự cập nhật: cron `*/5 * * * * cd /đường/dẫn/scan-app && ./run.sh --auto >> logs/cron.log 2>&1`.

---

## 5. Yêu cầu
| Thành phần | Yêu cầu |
|---|---|
| Máy tính trong tiệm | Windows 10/11 (hoặc macOS/Linux), RAM ≥ 4GB, không cần GPU. Bật suốt giờ mở cửa. |
| Điện thoại | iPhone/Android bất kỳ, cùng wifi |
| Máy in | A5. In giấy than: máy in kim 24 kim (vd Epson LQ-310/690). In laser/phun: in 2 bản |

## 6. Kiểm thử trước khi dùng thật
Test tự động (chạy trong `run`): `python backend/selfcheck.py`.

Test OCR bằng **giấy tờ thật của chính mình**: ghi tỉ lệ đúng theo từng ô — số CCCD, họ tên (có dấu),
địa chỉ, biển số, số khung, số máy. Ô nào sai nhiều thì chỉnh cách chụp hoặc thay model.

## 7. Bảo mật và dữ liệu cá nhân
- Ảnh CCCD là dữ liệu cá nhân (Nghị định 13/2023). App không lưu ảnh và không gọi dịch vụ ngoài.
- **Repo đang PUBLIC: không commit ảnh giấy tờ, tên, số CCCD, biển số, số khung thật** (kể cả trong code mẫu hay test). `.gitignore` chặn `samples/`, `*.jpg`, `*.png`, file test và benchmark.
- Chưa có đăng nhập. Chỉ dùng trong wifi nội bộ có mật khẩu. Giai đoạn sau thêm mã PIN.
- Tắt lưu ảnh tự động/đồng bộ ảnh đám mây của điện thoại nếu không muốn ảnh CCCD nằm trong thư viện ảnh.

## 8. Cấu trúc
```
scan-app/
├── backend/
│   ├── app.py              # API /api/scan: QR + OCR + gán trạng thái ô
│   ├── validators.py       # kiểm tra CCCD, biển số, số tiền thành chữ
│   ├── (test_*.py, benchmark.py chỉ có trên máy dev, không đưa lên GitHub)
│   └── selfcheck.py        # bước B3 (dùng chung mọi OS)
├── frontend/index.html     # chụp, form xanh/vàng/đỏ, preview A5, in
├── run.cmd / run.ps1       # Windows: cài + cập nhật + chạy
├── stop.cmd / stop.ps1     # Windows: dừng
├── setup-autostart.ps1     # Windows: tự chạy + tự cập nhật (Task Scheduler)
├── make-shortcut.cmd/.ps1  # Windows: 2 icon (ScanApp, ScanApp - Cai dat) ngoài Desktop + Start Menu
├── open-app.ps1            # Windows: việc icon ScanApp làm (bật ngầm nếu cần, mở trình duyệt)
├── make-mac-app.sh         # macOS: tạo ScanApp.app (icon) ra Desktop
├── assets/                 # icon (scanapp.png/.ico) + make_icon.py vẽ lại icon
├── run.sh / stop.sh        # macOS/Linux (và tự chuyển sang PowerShell nếu chạy trong Git Bash)
├── requirements.txt
├── .gitattributes          # .sh = LF, .ps1/.cmd = CRLF
└── .gitignore
```

## 9. Giới hạn đã biết
- Model OCR mặc định **chưa tối ưu dấu tiếng Việt**: họ tên từ OCR luôn bị đánh dấu vàng. Ưu tiên lấy từ QR.
- QR cà vẹt chỉ cho biển số (quan sát `85B1xxxxx-0-1`), không có số khung/số máy → phải OCR.
- QR CCCD thẻ căn cước mới (2024+) có thể chỉ chứa số định danh.
- "Hoàn thành" chỉ biết hộp thoại in đã đóng, không biết giấy ra thật.
- Khung hợp đồng dựng theo ảnh mẫu, chưa khớp từng chữ với mẫu thật; số hợp đồng chưa tự đánh.
- Trên Windows, dừng server là dừng ngay (không có tín hiệu "tắt nhẹ nhàng"); log `server.log` bị ghi đè mỗi lần start.
- Script Windows chưa được kiểm chứng trên máy thật.

## 10. Lộ trình
1. Chạy thử OCR trên ảnh thật, đo độ chính xác theo ô; chạy thử script trên máy Windows thật.
2. Số hợp đồng tự tăng; chỉnh khung theo mẫu thật.
3. In phía server để bấm In từ điện thoại và biết trạng thái job.
4. Lưu hồ sơ, tìm kiếm, nhắc hạn, backup.
5. Mã PIN đăng nhập.
