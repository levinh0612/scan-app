#!/usr/bin/env bash
# stop.sh — dừng server (nhẹ nhàng trước, ép buộc sau 15 giây)
set -uo pipefail
cd "$(dirname "$0")/.."

case "$(uname -s)" in   # Windows (Git Bash) → PowerShell
  MINGW*|MSYS*|CYGWIN*) exec powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$PWD/scripts/stop.ps1")";;
esac

PORT="${PORT:-8000}"
[ -f ".run/port" ] && PORT="$(cat .run/port)"   # cổng thật mà run.sh đã chọn
PID_FILE=".run/server.pid"

wait_dead() {   # $1=pid, $2=số giây
  for _ in $(seq 1 "$2"); do kill -0 "$1" 2>/dev/null || return 0; sleep 1; done
  return 1
}

stop_pid() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null || return 0
  echo "Dừng server (PID $pid)..."
  kill -TERM "$pid" 2>/dev/null
  if ! wait_dead "$pid" 15; then
    echo "Không tắt được nhẹ nhàng, ép dừng."
    kill -KILL "$pid" 2>/dev/null; wait_dead "$pid" 3
  fi
}

STOPPED=0
if [ "${1:-}" != "--keep-tunnel" ] && [ -f ".run/tunnel.pid" ]; then   # tắt tunnel https; --keep-tunnel = restart server mà giữ nguyên link
  TP="$(cat .run/tunnel.pid)"; pkill -P "$TP" 2>/dev/null; kill "$TP" 2>/dev/null; rm -f .run/tunnel.pid   # vòng giám sát + cloudflared con
fi
if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" 2>/dev/null; then stop_pid "$PID"; STOPPED=1; fi
  rm -f "$PID_FILE"
fi

# Dự phòng: còn tiến trình uvicorn của app này giữ cổng (vd pid file bị mất)
if command -v lsof >/dev/null 2>&1; then
  for pid in $(lsof -ti "tcp:${PORT}" -sTCP:LISTEN 2>/dev/null); do
    if ps -p "$pid" -o command= 2>/dev/null | grep -q "uvicorn app:app"; then stop_pid "$pid"; STOPPED=1; fi
  done
fi

[ "$STOPPED" -eq 1 ] && echo "Đã dừng." || echo "Server không chạy."
exit 0
