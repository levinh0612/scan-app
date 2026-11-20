#!/usr/bin/env bash
# Bật vòng giám sát tunnel https (cloudflared) nếu chưa chạy. Dùng bởi run.sh và bởi server (tự bật lại khi tunnel chết).
# Dùng: tunnel.sh [http|https] [port]
set -u
cd "$(dirname "$0")/.."
SCHEME="${1:-http}"; PORT="${2:-8000}"; RUN_DIR=.run; LOG_DIR=logs
mkdir -p "$RUN_DIR" "$LOG_DIR"
command -v cloudflared >/dev/null 2>&1 || exit 1
if [ -f "$RUN_DIR/tunnel.pid" ] && kill -0 "$(cat "$RUN_DIR/tunnel.pid")" 2>/dev/null; then exit 0; fi
echo "$SCHEME $PORT" > "$RUN_DIR/tunnel.want"       # server đọc file này: có file = cần tunnel
: > "$LOG_DIR/tunnel.log"
EXTRA=""; [ "$SCHEME" = "https" ] && EXTRA="--no-tls-verify"
nohup bash -c 'while true; do cloudflared tunnel "$@" 2>&1; sleep 20; : > "$0"; done' "$LOG_DIR/tunnel.log" $EXTRA --url "${SCHEME}://localhost:${PORT}" >> "$LOG_DIR/tunnel.log" 2>&1 &
echo $! > "$RUN_DIR/tunnel.pid"
