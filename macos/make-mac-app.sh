#!/usr/bin/env bash
# make-mac-app.sh — tạo icon macOS "ScanApp" (cửa sổ native: tự cài / tự bật server / hiện QR + link).
# Dùng:  ./macos/make-mac-app.sh            → tạo ~/Desktop/ScanApp.app
#        ./macos/make-mac-app.sh /Applications   → tạo ở thư mục khác
set -euo pipefail
cd "$(dirname "$0")/.."
[ "$(uname -s)" = "Darwin" ] || { echo "Script này chỉ dành cho macOS."; exit 1; }
ROOT="$PWD"
DEST="${1:-$HOME/Desktop}"
PY=".venv/bin/python"; [ -x "$PY" ] || PY="python3"
[ -f assets/scanapp.png ] || "$PY" assets/make_icon.py

# .icns từ PNG 1024 (dùng chung cho cả 2 app)
ICNS="$(mktemp -d)/ScanApp.icns"; SET="$(mktemp -d)/scanapp.iconset"; mkdir -p "$SET"
for s in 16 32 128 256 512; do
  sips -z $s $s assets/scanapp.png --out "$SET/icon_${s}x${s}.png" >/dev/null
  sips -z $((s*2)) $((s*2)) assets/scanapp.png --out "$SET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$SET" -o "$ICNS"

# mk_app <tên> <id> — tạo bộ khung .app; chương trình chạy do hàm gọi tự ghi vào Contents/MacOS/ScanApp
mk_app() {
  local app="$DEST/$1.app"
  # macOS (App Management) có thể không cho Terminal xoá bản app cũ → nhờ Finder bỏ vào Thùng rác
  rm -rf "$app" 2>/dev/null || osascript -e "tell application \"Finder\" to delete POSIX file \"$app\"" >/dev/null 2>&1 || true
  if [ -e "$app" ]; then echo "Không xoá được bản cũ: $app" >&2; echo "→ Kéo ScanApp trên Desktop vào Thùng rác rồi chạy lại file này." >&2; exit 1; fi
  mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
  cp "$ICNS" "$app/Contents/Resources/ScanApp.icns"
  cat > "$app/Contents/Info.plist" <<P
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>$1</string>
  <key>CFBundleDisplayName</key><string>$1</string>
  <key>CFBundleIdentifier</key><string>vn.scanapp.$2</string>
  <key>CFBundleExecutable</key><string>ScanApp</string>
  <key>CFBundleIconFile</key><string>ScanApp</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSAppTransportSecurity</key><dict><key>NSAllowsArbitraryLoads</key><true/></dict>
  <key>LSArchitecturePriority</key><array><string>arm64</string><string>x86_64</string></array>
</dict></plist>
P
  echo "$app"
}

# --- 1. ScanApp: cửa sổ native duy nhất. Chưa cài → cài; chưa chạy → bật server ngầm; rồi hiện QR + link cho điện thoại. ---
# Lưu ý macOS: app mở từ Finder KHÔNG được đọc ~/Documents → app chỉ gọi HTTP/osascript; việc đụng thư mục dự án giao cho Terminal (thu nhỏ).
APP="$(mk_app ScanApp main)"
if swiftc -O -swift-version 5 "$ROOT/macos/ScanApp.swift" -o "$APP/Contents/MacOS/ScanApp" 2>/tmp/scanapp-swiftc.log; then
  echo "$ROOT" > "$APP/Contents/Resources/root.txt"
else
  echo "Không biên dịch được cửa sổ ScanApp (thiếu Xcode Command Line Tools?). Chạy: xcode-select --install" >&2
  cat /tmp/scanapp-swiftc.log >&2; exit 1
fi
touch "$APP"

echo "Đã tạo trong $DEST:"
echo "  - ScanApp            : bấm đúp = cửa sổ ScanApp (chưa cài thì tự cài, chưa chạy thì tự bật server ngầm, rồi hiện QR + link cho điện thoại)."
echo "Kéo ScanApp vào Dock nếu muốn. Lần đầu nếu macOS hỏi quyền điều khiển Terminal → chọn OK."
