"""Gửi lệnh in từ máy chủ (không mở hộp thoại, không cần trình duyệt). Chọn máy in theo thứ tự:
  1. cấu hình .run/print.json  {"printer": "tên", "mode": "driver|escp", "host": "ip", "port": 9100, "dx": 0, "dy": 0}
  2. máy in mặc định của hệ điều hành (bỏ qua PDF/OneNote/Fax…)
mode "driver" (mặc định): vẽ ảnh A5 300dpi rồi in qua driver — chạy với MỌI máy in có driver (phun, laser, máy kim qua wifi).
mode "escp": gửi thẳng lệnh ESC/P2 tới host:9100 cho máy kim có card mạng — KHÔNG DẤU, chưa thử với máy thật."""
from __future__ import annotations

import json
import re
import socket
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

import layout
import printers
import render

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".run" / "print.json"
WIN = sys.platform.startswith("win")
WAIT_SECONDS = 120
_cancelled: set[str] = set()          # lệnh người dùng bấm Huỷ; luồng in kiểm tra cờ này giữa các lần theo dõi hàng đợi


def request_cancel(jid: str) -> None:
    _cancelled.add(jid)


class PrintError(Exception):
    """Lỗi có thể hiện nguyên văn cho nhân viên đọc."""


def load_config(path: Path = CONFIG) -> dict:
    try:
        c = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        c = {}
    return {"printer": str(c.get("printer", "")), "mode": c.get("mode", "driver"), "host": str(c.get("host", "")),
            "port": int(c.get("port", 9100)), "dx": float(c.get("dx", 0)), "dy": float(c.get("dy", 0))}


def pick_printer(cfg: dict, info: dict) -> str:
    if cfg["printer"]:
        return cfg["printer"]
    if info["status"] == "none" or not info["name"]:
        raise PrintError("Máy tính chưa cài máy in nào. Hãy thêm máy in wifi vào Windows/macOS rồi thử lại.")
    if info["status"] == "offline":
        raise PrintError(f"Máy in “{info['name']}” đang tắt hoặc không có trong mạng wifi.")
    return info["name"]


# ---------------- Chế độ driver ----------------
_PS_PRINT = r"""
param($Printer,$File,$Doc)
Add-Type -AssemblyName System.Drawing
$img=[System.Drawing.Image]::FromFile($File)
$pd=New-Object System.Drawing.Printing.PrintDocument
$pd.PrinterSettings.PrinterName=$Printer
if(-not $pd.PrinterSettings.IsValid){throw "Không tìm thấy máy in $Printer"}
$pd.DocumentName=$Doc
$pd.DefaultPageSettings.Margins=New-Object System.Drawing.Printing.Margins(0,0,0,0)
$a5=$pd.PrinterSettings.PaperSizes | Where-Object { $_.Kind -eq 'A5' } | Select-Object -First 1
if(-not $a5){$a5=New-Object System.Drawing.Printing.PaperSize('A5',583,827)}
$pd.DefaultPageSettings.PaperSize=$a5
$pd.DefaultPageSettings.Landscape=$false
$pd.add_PrintPage({param($s,$e)
  $g=$e.Graphics; $g.PageUnit=[System.Drawing.GraphicsUnit]::Display
  $g.TranslateTransform(-$e.PageSettings.HardMarginX,-$e.PageSettings.HardMarginY)
  $g.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
  $g.DrawImage($img,0,0,583,827); $e.HasMorePages=$false})
$pd.Print(); $img.Dispose()
"""


def _submit_driver(png: Path, printer: str, doc: str) -> str:
    if WIN:
        ps = Path(tempfile.gettempdir()) / "scanapp_print.ps1"
        ps.write_text(_PS_PRINT, encoding="utf-8-sig")
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps),
                            "-Printer", printer, "-File", str(png), "-Doc", doc],
                           capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
        if r.returncode:
            raise PrintError("Không gửi được lệnh in: " + (r.stderr.strip().splitlines() or ["lỗi không rõ"])[0][:200])
        return doc
    r = subprocess.run(["lp", "-d", printer, "-t", doc, "-o", "media=A5", "-o", "ppi=300", "-o", "fit-to-page=false",
                        str(png)], capture_output=True, text=True, timeout=30)
    m = re.search(r"request id is (\S+)", r.stdout)
    if r.returncode or not m:
        raise PrintError("Không gửi được lệnh in: " + (r.stderr.strip() or r.stdout.strip() or "lỗi không rõ")[:200])
    return m.group(1)


def _pending_driver(handle: str, printer: str) -> bool | str:
    """True = còn trong hàng đợi, False = đã ra khỏi hàng đợi, str = báo lỗi."""
    if WIN:
        ps = (f"Get-PrintJob -PrinterName '{printer}' -ErrorAction SilentlyContinue | "
              f"Where-Object {{ $_.DocumentName -eq '{handle}' }} | Select-Object -ExpandProperty JobStatus")
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                             timeout=15).stdout.strip()
        if not out:
            return False
        return "Máy in báo lỗi (hết giấy / kẹt giấy / mất kết nối)" if re.search(r"Error|Offline|PaperOut|PaperJam|UserIntervention", out, re.I) else True
    out = subprocess.run(["lpstat", "-W", "not-completed", "-o"], capture_output=True, text=True, timeout=10).stdout
    return handle in out


def _cancel_driver(handle: str) -> None:
    try:
        if not WIN:
            subprocess.run(["cancel", handle], capture_output=True, timeout=10)
    except Exception:
        pass


# ---------------- Chế độ ESC/P2 ----------------
def strip_accents(s: str) -> str:
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").encode("ascii", "replace").decode()


def escp_bytes(items: list[dict], dx: float = 0.0, dy: float = 0.0) -> bytes:
    """ESC/P2 24 kim: đơn vị 1/360 inch; đặt vị trí tuyệt đối từng chữ rồi in. Chữ cỡ 10.5cpi (LQ, Roman)."""
    u = lambda mm: max(0, round(mm / 25.4 * 360))  # noqa: E731
    out = bytearray(b"\x1b@\x1bx\x01\x1bk\x00\x1b(U\x01\x00\x0a")                 # reset, LQ, Roman, đơn vị 1/360 in
    out += b"\x1bP"                                                              # 10 cpi
    for it in sorted(items, key=lambda i: (i["y"], i["x"])):
        text = strip_accents(it["text"])
        if it.get("align") == "center":
            text_w = len(text) * 25.4 / 10
            x = it["x"] + max(0.0, (it["w"] - text_w) / 2)
        else:
            x = it["x"]
        xu, yu = u(x + dx), u(it["y"] + dy)
        out += b"\x1b(V\x02\x00" + bytes([yu & 255, yu >> 8])                    # vị trí dọc tuyệt đối
        out += b"\x1b$" + bytes([xu & 255, xu >> 8])                              # vị trí ngang tuyệt đối
        out += text.encode("ascii", "replace")
    return bytes(out) + b"\x0c"


def _send_escp(data: bytes, host: str, port: int) -> None:
    if not host:
        raise PrintError("Chế độ ESC/P cần ghi địa chỉ IP máy in (host) trong .run/print.json")
    try:
        with socket.create_connection((host, port), timeout=5) as s:
            s.sendall(data)
    except OSError as e:
        raise PrintError(f"Không kết nối được máy in {host}:{port} ({e.strerror or e})")


# ---------------- Điều phối ----------------
def _png_path(jid: str) -> Path:
    return Path(tempfile.gettempdir()) / f"scanapp_{jid}.png"      # chứa dữ liệu cá nhân: xoá ngay khi in xong


def print_snapshot(snap: dict, jid: str, cfg: dict | None = None, info: dict | None = None):
    """Gửi một lệnh in. Trả về (handle, printer) để theo dõi hàng đợi; handle=None nếu không theo dõi được."""
    cfg = cfg or load_config()
    tpl = layout.load_template()
    items = layout.build_items(snap, tpl)
    if not items:
        raise PrintError("Hồ sơ trống, không có gì để in.")
    if cfg["mode"] == "escp":
        _send_escp(escp_bytes(items, cfg["dx"], cfg["dy"]), cfg["host"], cfg["port"])
        return None, cfg["host"]
    printer = pick_printer(cfg, info or printers.cached(ttl=0))
    img, _ = render.render(items, tpl["page"], cfg["dx"], cfg["dy"])
    png = _png_path(jid)
    render.save_png(img, png)
    return _submit_driver(png, printer, f"ScanApp-{jid}"), printer


def print_image(img, jid: str, cfg: dict | None = None, info: dict | None = None) -> str:
    """In một ảnh đã vẽ (biên nhận, in thử) qua driver máy in. Trả về tên máy in."""
    cfg = cfg or load_config()
    if cfg["mode"] == "escp":
        raise PrintError("Máy in kim (ESC/P) chỉ in được phiếu hồ sơ, chưa in được mẫu này. Hãy dùng máy in có driver.")
    printer = pick_printer(cfg, info or printers.cached(ttl=0))
    png = _png_path(jid)
    try:
        render.save_png(img, png)
        _submit_driver(png, printer, f"ScanApp-{jid}")
    finally:
        png.unlink(missing_ok=True)
    return printer


def run_job(store, jid: str, snap: dict, sleep=time.sleep, cfg: dict | None = None) -> None:
    """Chạy trong luồng nền: gửi lệnh in rồi theo dõi hàng đợi → da_gui (lệnh đã rời hàng đợi) hoặc loi + lý do."""
    try:
        handle, printer = print_snapshot(snap, jid, cfg)
        if handle is None:
            store.update(jid, "da_gui")
            return
        for _ in range(WAIT_SECONDS // 2):
            if jid in _cancelled:
                _cancel_driver(handle)
                store.update(jid, "loi", "Đã huỷ lệnh in.")
                return
            state = _pending_driver(handle, printer)
            if state is False:
                store.update(jid, "da_gui")
                return
            if isinstance(state, str):
                _cancel_driver(handle)
                store.update(jid, "loi", state)
                return
            sleep(2)
        _cancel_driver(handle)
        store.update(jid, "loi", f"Máy in “{printer}” không nhận lệnh sau {WAIT_SECONDS} giây (tắt máy, hết giấy hoặc mất wifi?). Đã huỷ lệnh, hãy kiểm tra rồi bấm In lại.")
    except PrintError as e:
        store.update(jid, "loi", str(e))
    except Exception as e:                                  # không để luồng chết im lặng
        store.update(jid, "loi", f"Lỗi khi in: {e}")
    finally:
        _cancelled.discard(jid)
        _png_path(jid).unlink(missing_ok=True)
