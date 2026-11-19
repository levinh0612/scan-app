#!/usr/bin/env bash
# =============================================================================
# run.sh — cài đặt, cập nhật và chạy server quét giấy tờ (macOS / Linux)
#
#   B1. Tải tài nguyên cần thiết (git, python >= 3.10, venv, thư viện)
#   B2. Pull code mới từ GitHub
#   B3. Kiểm tra (cú pháp, test, import)  — lỗi thì hoàn tác code, KHÔNG đụng server đang chạy
#   (chạy không tham số trong terminal → hiện menu chọn)
#   B4. Start nếu chưa chạy, restart nếu đang chạy (kèm health check, lỗi thì quay về bản cũ)
#
# Dùng:  ./scripts/run.sh              (đầy đủ B1-B4)
#        ./scripts/run.sh --no-pull    (bỏ B2)
#        ./scripts/run.sh --tunnel     (thêm link https công khai để điện thoại dùng camera; cần cloudflared)
#        PORT=9000 ./scripts/run.sh    (đổi cổng, mặc định 8000)
# Dừng:  ./scripts/stop.sh
# =============================================================================
set -Eeuo pipefail
cd "$(dirname "$0")/.."

PORT="${PORT:-8000}"
RUN_DIR=".run"; LOG_DIR="logs"; PID_FILE="$RUN_DIR/server.pid"; LOG_FILE="$LOG_DIR/server.log"
# server đang chạy ở cổng đã tự chọn lần trước → dùng lại cổng đó cho kiểm tra sức khoẻ
[ -f "$RUN_DIR/port" ] && [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null && PORT="$(cat "$RUN_DIR/port")"

# ---------- Nhận diện OS: Windows (Git Bash/MSYS/Cygwin) → giao cho PowerShell ----------
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    PS_ARGS=()
    for a in "$@"; do
      case "$a" in --no-pull) PS_ARGS+=("-NoPull");; --auto) PS_ARGS+=("-Auto");; --tunnel) PS_ARGS+=("-Tunnel");; --https) PS_ARGS+=("-Https");; *) PS_ARGS+=("$a");; esac
    done
    exec powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$PWD/scripts/run.ps1")" "${PS_ARGS[@]}"
    ;;
esac

DO_PULL=1; AUTO=0; TUNNEL="${TUNNEL:-1}"; HTTPS="${HTTPS:-0}"   # mặc định: link https qua tunnel Cloudflare (camera điện thoại chạy, không phụ thuộc wifi); --no-tunnel để tắt
for a in "$@"; do
  case "$a" in
    --no-pull) DO_PULL=0;;
    --auto)    AUTO=1;;
    --tunnel)  TUNNEL=1;;
    --no-tunnel) TUNNEL=0;;
    --https)   HTTPS=1;;
    --http)    HTTPS=0;;
    *) echo "Tham số không hợp lệ: $a (dùng --no-pull, --auto, --tunnel, --no-tunnel, --http, --https)"; exit 2;;
  esac
done

# Đã bấm "Dừng chạy app": tác vụ tự động (--auto) không được bật lại; chạy tay hoặc mở cửa sổ ScanApp thì xoá cờ
if [ "$AUTO" -eq 1 ] && [ -f .run/stopped ]; then echo "ScanApp đang được dừng thủ công — bỏ qua."; exit 0; fi
[ "$AUTO" -eq 0 ] && rm -f .run/stopped

# ---------- Menu chọn (chỉ khi chạy tay, không tham số, có terminal) ----------
if [ "$#" -eq 0 ] && [ -t 0 ] && [ -t 1 ]; then
  echo
  echo "  QUÉT GIẤY TỜ — chọn cách chạy"
  echo "   1) Chạy đầy đủ            (cập nhật code từ GitHub → kiểm tra → chạy)"
  echo "   2) Chạy, không cập nhật   (nhanh, dùng code hiện có)"
  echo "   3) Chạy + link https      (điện thoại dùng được camera; cần cloudflared)"
  echo "   4) Dừng server"
  echo "   5) Chạy + https trong wifi (cert tự ký, không cần internet; điện thoại bấm \"tiếp tục\" 1 lần)"
  echo "   0) Thoát"
  printf "  Chọn [1]: "; read -r CHOICE || CHOICE=0
  case "${CHOICE:-1}" in
    1) ;;
    2) DO_PULL=0;;
    3) DO_PULL=0; TUNNEL=1;;
    4) exec ./scripts/stop.sh;;
    5) DO_PULL=0; HTTPS=1;;
    0) exit 0;;
    *) echo "Lựa chọn không hợp lệ."; exit 2;;
  esac
fi
mkdir -p "$RUN_DIR" "$LOG_DIR"

log()  { printf '\033[1;34m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*"; }
warn() { printf '\033[1;33m[CẢNH BÁO]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[LỖI]\033[0m %s\n' "$*" >&2; exit 1; }
trap 'die "Script dừng ở dòng $LINENO (lệnh: $BASH_COMMAND)"' ERR

SUDO=""; [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1 && SUDO="sudo"

# ---------- tiện ích ----------
pkg_install() {   # $1 = tên gói theo brew/apt/dnf
  if   command -v brew    >/dev/null 2>&1; then brew install "$1"
  elif command -v apt-get >/dev/null 2>&1; then $SUDO apt-get update -qq && $SUDO apt-get install -y -qq "$1"
  elif command -v dnf     >/dev/null 2>&1; then $SUDO dnf install -y -q "$1"
  elif command -v yum     >/dev/null 2>&1; then $SUDO yum install -y -q "$1"
  else die "Không có trình quản lý gói. Hãy tự cài: $1 (macOS: cài Homebrew từ https://brew.sh trước)"; fi
}

find_python() {   # in ra đường dẫn python >= 3.10
  for p in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)' 2>/dev/null; then
      command -v "$p"; return 0
    fi
  done
  return 1
}

sha() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

sync_deps() {     # chỉ cài lại khi backend/requirements.txt đổi
  local want have=""; want="$(sha backend/requirements.txt)"
  [ -f .venv/.req.sha ] && have="$(cat .venv/.req.sha)"
  if [ "$want" = "$have" ]; then log "Thư viện đã đủ, bỏ qua."; return 0; fi
  log "Cài thư viện (lần đầu có thể mất vài phút nếu mạng chậm)..."
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python .venv/bin/python -r backend/requirements.txt
  else
    .venv/bin/python -m pip install --default-timeout 60 --retries 5 -q -r backend/requirements.txt
  fi
  echo "$want" > .venv/.req.sha
}

is_running() { [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; }

SCHEME=http; SSL_ARGS=()
if [ "$HTTPS" = "1" ]; then
  _IP="$( (ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}') || true)"
  CERT_OUT="$(.venv/bin/python backend/make_cert.py "$_IP" 2>/dev/null)" || die "Không tạo được chứng chỉ https (thiếu thư viện cryptography? chạy lại bước cài)"
  SSL_ARGS=(--ssl-certfile "$(echo "$CERT_OUT" | sed -n 1p)" --ssl-keyfile "$(echo "$CERT_OUT" | sed -n 2p)")
  SCHEME=https
fi
health_ok() { curl -kfsS -m 3 "${SCHEME}://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; }

port_busy() {
  if command -v lsof >/dev/null 2>&1; then lsof -ti "tcp:$1" -sTCP:LISTEN >/dev/null 2>&1
  else (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; fi
}
start_server() {
  if ! is_running; then   # cổng bận bởi chương trình khác → tự chọn cổng trống kế tiếp (tối đa 30 cổng)
    local want="$PORT" n=0
    while port_busy "$PORT" && [ "$n" -lt 30 ]; do PORT=$((PORT + 1)); n=$((n + 1)); done
    port_busy "$PORT" && die "Không tìm được cổng trống từ ${want}. Đổi cổng: PORT=9000 ./scripts/run.sh"
    [ "$PORT" != "$want" ] && warn "Cổng ${want} đang bị chương trình khác dùng → dùng cổng ${PORT}."
  fi
  echo "$PORT" > "$RUN_DIR/port"
  nohup .venv/bin/python -m uvicorn app:app --app-dir backend --host 0.0.0.0 --port "$PORT" ${SSL_ARGS[@]+"${SSL_ARGS[@]}"} >> "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  for _ in $(seq 1 30); do
    health_ok && return 0
    kill -0 "$(cat "$PID_FILE")" 2>/dev/null || return 1   # tiến trình đã chết
    sleep 1
  done
  return 1
}

# =============================================================================
log "B1. Chuẩn bị tài nguyên"
# =============================================================================
command -v git  >/dev/null 2>&1 || { log "Cài git..."; pkg_install git; }
command -v curl >/dev/null 2>&1 || { log "Cài curl..."; pkg_install curl; }

PY="$(find_python || true)"
if [ -z "$PY" ]; then
  log "Chưa có Python >= 3.10, đang cài..."
  if command -v brew >/dev/null 2>&1; then pkg_install python@3.13; else pkg_install python3; fi
  PY="$(find_python || true)"; [ -z "$PY" ] && die "Cài Python xong nhưng vẫn không tìm thấy bản >= 3.10"
fi
log "Python: $("$PY" --version) ($PY)"

if [ ! -x .venv/bin/python ]; then
  log "Tạo môi trường ảo .venv"
  "$PY" -m venv .venv || { command -v apt-get >/dev/null 2>&1 && pkg_install python3-venv && "$PY" -m venv .venv; }
fi
sync_deps

# =============================================================================
log "B2. Pull code"
# =============================================================================
PREV_COMMIT=""; PULLED=0
if [ "$DO_PULL" -eq 0 ]; then
  log "Bỏ qua pull (--no-pull)."
elif [ ! -d .git ] || ! git remote get-url origin >/dev/null 2>&1; then
  warn "Thư mục chưa phải git repo hoặc chưa có remote 'origin' → bỏ qua pull."
elif [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  warn "Có thay đổi chưa commit trong thư mục → bỏ qua pull để không ghi đè."
else
  PREV_COMMIT="$(git rev-parse HEAD)"
  BRANCH="$(git branch --show-current)"
  git fetch --quiet origin
  if git rev-parse --abbrev-ref "@{u}" >/dev/null 2>&1; then git pull --ff-only --quiet
  else git pull --ff-only --quiet origin "$BRANCH"; fi
  NEW_COMMIT="$(git rev-parse HEAD)"
  if [ "$PREV_COMMIT" = "$NEW_COMMIT" ]; then log "Đã là bản mới nhất ($(git rev-parse --short HEAD))."
  else PULLED=1; log "Cập nhật $(git rev-parse --short "$PREV_COMMIT") → $(git rev-parse --short "$NEW_COMMIT")"; sync_deps; fi
fi

AUTO_SKIP_CHECK() { [ "$AUTO" -eq 1 ] && [ "$PULLED" -eq 0 ] && is_running && health_ok; }
if AUTO_SKIP_CHECK; then log "Auto: không có thay đổi, server đang chạy tốt."; exit 0; fi

rollback_code() {
  if [ "$PULLED" -eq 1 ] && [ -n "$PREV_COMMIT" ]; then
    warn "Hoàn tác code về $(git rev-parse --short "$PREV_COMMIT")"
    git reset --hard --quiet "$PREV_COMMIT"; PULLED=0; sync_deps || true
  fi
}

# =============================================================================
log "B3. Kiểm tra"
# =============================================================================
check() { .venv/bin/python backend/selfcheck.py; }
trap - ERR
if ! check; then
  rollback_code
  trap 'die "Script dừng ở dòng $LINENO"' ERR
  die "Kiểm tra thất bại. Server đang chạy (nếu có) KHÔNG bị thay đổi."
fi
trap 'die "Script dừng ở dòng $LINENO (lệnh: $BASH_COMMAND)"' ERR
log "Kiểm tra đạt."

# =============================================================================
log "B4. Khởi động"
# =============================================================================
if is_running; then
  log "Server đang chạy (PID $(cat "$PID_FILE")) → restart"
  ./scripts/stop.sh --keep-tunnel
else
  log "Server chưa chạy → start"
fi

if ! start_server; then
  warn "Server không lên được. 20 dòng log cuối:"; tail -n 20 "$LOG_FILE" >&2 || true
  ./scripts/stop.sh --keep-tunnel || true
  if [ "$PULLED" -eq 1 ]; then
    rollback_code
    log "Thử chạy lại bản cũ..."
    start_server && die "Bản mới lỗi, đã quay về bản cũ và đang chạy. Xem $LOG_FILE" || die "Cả bản cũ cũng không chạy. Xem $LOG_FILE"
  fi
  die "Không khởi động được. Xem $LOG_FILE"
fi

IP="$( (ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}') || true)"
log "Server đang chạy (PID $(cat "$PID_FILE"))"
echo
echo "   Máy tính   ${SCHEME}://localhost:${PORT}"
if [ -n "${IP:-}" ]; then
  echo "   Cùng wifi  ${SCHEME}://${IP}:${PORT}"
  [ "$HTTPS" = "1" ] && echo "   (lần đầu điện thoại báo \"không an toàn\": bấm Nâng cao → Tiếp tục)"
  WIFI_QR=""; [ "$TUNNEL" != "1" ] && [ "$SCHEME" = "https" ] && WIFI_QR="$(.venv/bin/python backend/qr_print.py "Cùng wifi=${SCHEME}://${IP}:${PORT}" 2>/dev/null || true)"   # có tunnel thì chỉ hiện QR link https
  if [ -n "$WIFI_QR" ]; then echo; echo "$WIFI_QR"; echo; QR_LINES=$(( $(echo "$WIFI_QR" | wc -l) + 2 )); fi   # in ngay, không chờ tunnel
fi
if [ "$TUNNEL" = "1" ]; then
  if ! command -v cloudflared >/dev/null 2>&1; then
    warn "Chưa có cloudflared nên không tạo được link https. Cài: brew install cloudflared"
  else
    if [ -f "$RUN_DIR/tunnel.pid" ] && kill -0 "$(cat "$RUN_DIR/tunnel.pid")" 2>/dev/null && grep -aqE 'trycloudflare\.com' "$LOG_DIR/tunnel.log" 2>/dev/null; then
      :   # tunnel đang chạy từ lần trước → giữ nguyên để link không đổi (cập nhật tự động chạy lại run.sh định kỳ)
    else
    : > "$LOG_DIR/tunnel.log"
    # Vòng giám sát: Cloudflare hay từ chối tạm thời (429 khi tạo link liên tục) hoặc tunnel rớt → tự thử lại sau 20 giây, không cần chạy lại run.sh
    nohup bash -c 'while true; do cloudflared tunnel "$@" 2>&1; sleep 20; : > "$0"; done' "$LOG_DIR/tunnel.log" $([ "$HTTPS" = "1" ] && echo --no-tls-verify) --url "${SCHEME}://localhost:${PORT}" >> "$LOG_DIR/tunnel.log" 2>&1 &
    echo $! > "$RUN_DIR/tunnel.pid"
    fi
    URL=""
    printf "   Link https  đang tạo (chờ vài giây)"
    for _ in $(seq 1 100); do                       # kiểm tra mỗi 0,3 giây, tối đa 30 giây
      URL="$(grep -aoE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG_DIR/tunnel.log" | head -1 || true)"
      [ -n "$URL" ] && break; printf "."; sleep 0.3
    done
    if [ -n "$URL" ]; then                          # tên miền hiện trong log trước khi truy cập được → chờ tới khi thật sự trả lời
      H="${URL#https://}"
      for _ in $(seq 1 25); do                      # tối đa 25 giây; hỏi thêm DNS 1.1.1.1 vì máy này có thể nhớ tạm tên miền chưa tồn tại
        curl -fsS -m 3 -o /dev/null "$URL/api/health" 2>/dev/null && break
        RIP="$(dig +short @1.1.1.1 "$H" 2>/dev/null | head -1 || true)"
        [ -n "$RIP" ] && curl -fsS -m 3 -o /dev/null --resolve "$H:443:$RIP" "$URL/api/health" 2>/dev/null && break
        printf "."; sleep 1
      done
    fi
    printf "\r\033[K"
    if [ -n "$URL" ]; then
      BOTH=""   # chỉ hiện link https (camera điện thoại chỉ chạy trên https)
      [ -t 1 ] && [ "${QR_LINES:-0}" -gt 0 ] && printf "\033[%dA\033[J" "$QR_LINES"   # xoá QR wifi cũ, vẽ lại 2 cột đúng chỗ đó
      echo "   Link https $URL"
      echo "              (dùng được camera; KHÔNG có mật khẩu, chỉ gửi người tin cậy)"
      if [ -n "$BOTH" ]; then echo; echo "$BOTH"; echo
      else echo; .venv/bin/python backend/qr_print.py "Link https=$URL" 2>/dev/null || true; echo; fi
      echo "   (nếu điện thoại chưa vào được: chờ vài giây rồi tải lại)"
    else
      warn "Chưa lấy được link https, xem $LOG_DIR/tunnel.log"
    fi
  fi
fi
echo "   Log         : $LOG_FILE      Dừng: ./scripts/stop.sh"
