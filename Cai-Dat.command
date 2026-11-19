#!/usr/bin/env bash
# Bấm đúp file này (một lần): tạo icon ScanApp ngoài Desktop rồi mở luôn.
# Lần đầu, cửa sổ ScanApp tự cài môi trường (vài phút), tự bật server ngầm, rồi hiện QR + link cho điện thoại.
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
chmod +x run.sh stop.sh make-mac-app.sh 2>/dev/null
./make-mac-app.sh && open "$HOME/Desktop/ScanApp.app"
echo; echo "Xong. Dùng icon ScanApp ngoài Desktop. Đóng cửa sổ này được."
