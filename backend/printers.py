"""Hỏi hệ điều hành của máy chủ xem máy in đã cài/đang bật chưa (Windows: CIM, macOS/Linux: lpstat).
Chỉ biết trạng thái ở mức hệ điều hành — KHÔNG biết hết giấy/mực/kẹt giấy."""
from __future__ import annotations

import json
import re
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import unquote, urlparse

VIRTUAL = re.compile(r"pdf|onenote|xps|fax|send to|document writer|snagit", re.I)
WIN_STATUS = {3: "ready", 4: "printing", 5: "printing", 6: "error", 7: "offline", 1: "error", 2: "error"}


def parse_windows(raw: str) -> list[dict]:
    if not raw.strip():
        return []
    data = json.loads(raw)
    if isinstance(data, dict):
        data = [data]
    out = []
    for p in data:
        state = WIN_STATUS.get(p.get("PrinterStatus"), "error")
        if p.get("WorkOffline"):
            state = "offline"
        out.append({"name": p.get("Name", ""), "state": state, "default": bool(p.get("Default"))})
    return out


def parse_lpstat(printers_out: str, default_out: str) -> list[dict]:
    m = re.search(r"destination:\s*(\S+)", default_out)
    default = m.group(1) if m else None
    out = []
    for line in printers_out.splitlines():
        m = re.match(r"printer\s+(\S+)\s+(.*)", line)
        if not m:
            continue
        name, rest = m.group(1), m.group(2).lower()
        if "disabled" in rest:
            state = "offline"
        elif "now printing" in rest or "printing" in rest:
            state = "printing"
        elif "idle" in rest:
            state = "ready"
        else:
            state = "error"
        out.append({"name": name, "state": state, "default": name == default})
    return out


def parse_lpstat_v(text: str) -> dict[str, str]:
    """'device for NAME: URI' → {NAME: URI}"""
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"device for (\S+):\s*(\S+)", text)}


def _tcp_ok(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def reachable(uri: str) -> bool | None:
    """Thử liên lạc thật tới máy in. True/False; None = không kiểm tra được loại kết nối này."""
    u = urlparse(uri)
    if u.scheme in ("ipp", "ipps", "http", "https", "socket", "lpd") and u.hostname:
        port = u.port or {"ipp": 631, "ipps": 631, "http": 631, "https": 631, "socket": 9100, "lpd": 515}[u.scheme]
        return _tcp_ok(u.hostname, port)
    if u.scheme == "dnssd":                                   # Bonjour: tìm dịch vụ trên mạng LAN
        m = re.match(r"^(.*)\.(_[a-z]+\._(?:tcp|udp))\.(\w+)$", unquote(u.netloc).rstrip("."))
        if not m:
            return None
        try:
            out = subprocess.run(["dns-sd", "-L", m.group(1), m.group(2), m.group(3)], capture_output=True, text=True, timeout=3).stdout
        except subprocess.TimeoutExpired as e:               # dns-sd chạy mãi, lấy phần đã in ra
            out = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        except OSError:
            return None
        return "can be reached" in out
    if u.scheme == "usb":
        vendor = unquote(u.netloc).split()[0].lower()
        try:
            return vendor in subprocess.run(["system_profiler", "SPUSBDataType"], capture_output=True, text=True, timeout=8).stdout.lower()
        except Exception:
            return None
    return None


def verify(printers: list[dict], uris: dict[str, str], check=reachable) -> list[dict]:
    """Máy in 'ready' theo hệ điều hành nhưng không liên lạc được → offline (driver cài sẵn ≠ đang kết nối)."""
    for p in printers:
        if p["state"] in ("ready", "printing") and p["name"] in uris:
            ok = check(uris[p["name"]])
            if ok is False:
                p["state"], p["reason"] = "offline", "Đã cài driver nhưng không tìm thấy máy in trên mạng/USB"
    return printers


def summarize(printers: list[dict]) -> dict:
    real = [p for p in printers if not VIRTUAL.search(p["name"])]
    if not real:
        return {"status": "none", "name": "", "printers": []}
    chosen = next((p for p in real if p["default"]), real[0])
    return {"status": chosen["state"], "name": chosen["name"], "printers": real}


def _run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=6, encoding="utf-8", errors="replace").stdout


def detect() -> dict:
    try:
        if sys.platform.startswith("win"):
            ps = "Get-CimInstance Win32_Printer | Select-Object Name,Default,WorkOffline,PrinterStatus | ConvertTo-Json -Compress"
            return summarize(parse_windows(_run(["powershell", "-NoProfile", "-Command", ps])))
        ps = parse_lpstat(_run(["lpstat", "-p"]), _run(["lpstat", "-d"]))
        return summarize(verify(ps, parse_lpstat_v(_run(["lpstat", "-v"]))))
    except Exception:
        return {"status": "unknown", "name": "", "printers": []}


_cache: dict = {"t": 0.0, "v": None}
_lock = threading.Lock()


def cached(ttl: float = 5.0) -> dict:
    with _lock:
        if _cache["v"] is None or time.time() - _cache["t"] > ttl:
            _cache["v"], _cache["t"] = detect(), time.time()
        return _cache["v"]
