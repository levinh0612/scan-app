#!/usr/bin/env bash
# Bấm đúp file này (một lần): tạo icon ScanApp ngoài Desktop rồi mở luôn.
# Lần đầu, cửa sổ ScanApp tự cài môi trường (vài phút), tự bật server ngầm, rồi hiện QR + link cho điện thoại.
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
chmod +x scripts/run.sh scripts/stop.sh macos/make-mac-app.sh 2>/dev/null
if ./macos/make-mac-app.sh; then
  open "$HOME/Desktop/ScanApp.app"
  echo; echo "Xong. Cửa sổ ScanApp đang mở; lần sau bấm icon ScanApp ngoài Desktop. Đóng cửa sổ này được."
else
  echo; echo "CHƯA XONG — xem dòng lỗi ở trên."
fi
