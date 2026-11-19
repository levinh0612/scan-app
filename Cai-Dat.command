#!/usr/bin/env bash
# Bấm đúp file này để cài ScanApp trên Mac: cài môi trường, chạy thử, tạo icon ngoài Desktop.
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
chmod +x run.sh stop.sh make-mac-app.sh 2>/dev/null
./run.sh --no-pull --tunnel && ./make-mac-app.sh
echo; echo "Xong. Dùng icon ScanApp ngoài Desktop. Đóng cửa sổ này được."
read -r -p "Bấm Enter để đóng..." _
