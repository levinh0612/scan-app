"""API quét giấy tờ — chạy hoàn toàn offline. Ảnh quét chỉ xử lý trong RAM; chỉ khi lưu hợp đồng mới có ảnh nén lưu thành file (data/anh)."""
from __future__ import annotations
import cv2
import io
import logging
import os
import re
import subprocess
import threading
from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
import time
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pathlib import Path

import contracts
import images
import printers
import settings
import stack
from ocr_parse import decode_image, parse_cavet, parse_cccd, read_cavet_multi, read_qr, run_ocr, trace
from routes_contracts import router as contracts_router
from routes_jobs import router as jobs_router
from routes_print import router as print_router
from webutil import _is_local, _need_local





ROOT = Path(__file__).resolve().parent.parent


app = FastAPI(title="Scan cầm đồ")
app.include_router(contracts_router)
app.include_router(jobs_router)
app.include_router(print_router)


def _tunnel_revoked(log: Path) -> bool:
    """Link tunnel tạm (trycloudflare) đôi khi bị Cloudflare thu hồi (máy ngủ lâu, mạng đổi): tiến trình vẫn sống và cứ thử lại
    với lỗi 'Tunnel not found' nhưng điện thoại không vào được nữa. Nhận ra qua phần cuối nhật ký."""
    try:
        with open(log, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 3000))
            return b"Tunnel not found" in f.read()
    except OSError:
        return False


def _kill_tunnel(pid: int, run: Path) -> None:
    subprocess.run(["pkill", "-P", str(pid)], capture_output=True)    # cloudflared con
    try:
        os.kill(pid, 15)                                              # vòng bash giám sát
    except OSError:
        pass
    (run / "tunnel.pid").unlink(missing_ok=True)


def _tunnel_watchdog() -> None:
    """Tunnel https chết (bị kill, máy ngủ, run.sh bị ngắt giữa chừng…) thì tự bật lại, chủ tiệm không phải làm gì.
    Không bật khi: đang dừng thủ công (.run/stopped) hoặc chạy với --no-tunnel (.run/no-tunnel)."""
    import time
    root = Path(__file__).resolve().parent.parent
    run = root / ".run"
    while True:
        time.sleep(10)
        try:
            if (run / "stopped").exists() or (run / "no-tunnel").exists():
                continue
            pid = int((run / "tunnel.pid").read_text().strip()) if (run / "tunnel.pid").exists() else 0
            alive = False
            if pid:
                try:
                    os.kill(pid, 0)
                    alive = True
                except OSError:
                    pass
            if alive and _tunnel_revoked(root / "logs" / "tunnel.log"):
                _kill_tunnel(pid, run)                       # cloudflared còn chạy nhưng link đã bị Cloudflare thu hồi: bật lại để lấy link mới
                alive = False
            if not alive:
                scheme = (run / "scheme").read_text().strip() if (run / "scheme").exists() else "http"
                port = (run / "port").read_text().strip() if (run / "port").exists() else "8000"
                subprocess.run([str(root / "scripts" / "tunnel.sh"), scheme, port], timeout=20, capture_output=True)
        except Exception:
            logging.getLogger("tunnel").warning("Bật lại tunnel lỗi, thử lại vòng sau", exc_info=True)


def _backup_loop() -> None:
    """Sao lưu kho hợp đồng khi khởi động rồi mỗi 6 giờ (mỗi ngày giữ 1 bản)."""
    import time
    while True:
        try:
            contracts.backup()
            images.cleanup(contracts.closed_for_cleanup(), settings.get()["anh_giu_ngay"])    # ảnh hợp đồng đã đóng quá hạn giữ → xóa
        except Exception as e:      # không để lỗi sao lưu làm sập server
            print(f"[BACKUP] lỗi: {e}", flush=True)
        time.sleep(6 * 3600)


@app.on_event("startup")
def _start_watchdog() -> None:
    threading.Thread(target=_backup_loop, daemon=True).start()
    if os.name != "nt":
        threading.Thread(target=_tunnel_watchdog, daemon=True).start()


# ---------------- API ----------------
def slog(tag: str, msg: str) -> None:
    print(f"[{tag} {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _cip(request: Request) -> str:
    h = request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "?")
    return h[:20] + "…" if len(h) > 20 else h


@app.post("/api/scan")
async def scan(request: Request, cccd_front: UploadFile | None = File(None), cccd_back: UploadFile | None = File(None),
               cavet: UploadFile | None = File(None)):
    t_scan = time.perf_counter()
    out: dict = {}
    warnings: list[str] = []

    async def load(f):
        return decode_image(await f.read()) if f else None

    imgs = {"front": await load(cccd_front), "back": await load(cccd_back), "cavet": await load(cavet)}
    for k, v in imgs.items():
        if v is None and {"front": cccd_front, "back": cccd_back, "cavet": cavet}[k] is not None:
            warnings.append(f"Không mở được ảnh {k}")

    qr_cccd = next((q for q in (read_qr(imgs["front"]) if imgs["front"] is not None else None,
                                read_qr(imgs["back"]) if imgs["back"] is not None else None) if q), None)
    qr_cavet = read_qr(imgs["cavet"]) if imgs["cavet"] is not None else None

    f_lines = run_ocr(imgs["front"], "front") if imgs["front"] is not None else None
    b_lines = run_ocr(imgs["back"], "back") if imgs["back"] is not None else None
    if imgs["front"] is not None or imgs["back"] is not None:
        parse_cccd(f_lines, b_lines, qr_cccd, out, warnings)
    if imgs["cavet"] is not None:
        cv_out, c_lines = read_cavet_multi(imgs["cavet"], qr_cavet, warnings)
        trace("cavet", imgs["cavet"], c_lines, qr_cavet)
        out.update(cv_out)
    for tag, im, ln in (("front", imgs["front"], f_lines), ("back", imgs["back"], b_lines)):
        if im is not None:
            trace(tag, im, ln, qr_cccd)
    slog("SCAN", f"{_cip(request)} ảnh={','.join(k for k, v in imgs.items() if v is not None)} ms={round((time.perf_counter()-t_scan)*1000)} "
         + " ".join(f"{k}={v.get('status')}" for k, v in out.items()) + (f" | cảnh báo={len(warnings)}" if warnings else ""))
    return {"fields": out, "warnings": warnings}


@app.post("/api/stack")
async def stack_burst(images: list[UploadFile] = File(...)):
    """Gộp loạt khung hình liên tiếp (chọn khung nét nhất + căn chỉnh + trung bình) thành 1 ảnh JPEG. Không lưu gì."""
    frames = []
    for f in images[:10]:
        im = decode_image(await f.read())
        if im is not None:
            frames.append(im)
    if not frames:
        raise HTTPException(400, "Ảnh không hợp lệ")
    out, info = stack.stack_frames(frames)
    ok, buf = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return Response(buf.tobytes(), media_type="image/jpeg", headers={"X-Stack-Used": str(info["used"]), "X-Stack-N": str(info["n"])})


@app.post("/api/peek")
async def peek(request: Request, kind: str = Form(...), image: UploadFile = File(...)):
    """Xem trước trực tiếp trên màn hình camera: đọc nhanh 1 khung hình, KHÔNG lưu, KHÔNG ghi log nội dung."""
    t0 = time.perf_counter()
    raw = await image.read()
    img = decode_image(raw)
    if img is None or kind not in ("cavet", "cccd_front", "cccd_back"):
        raise HTTPException(400, "Ảnh không hợp lệ")
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sharp = float(cv2.Laplacian(g, cv2.CV_64F).var())
    glare = float((g >= 250).mean())          # tỉ lệ điểm cháy sáng (bóng đèn/phản chiếu lên thẻ nhựa)
    qr = read_qr(img)
    lines = run_ocr(img, "peek")
    out: dict = {}
    if kind == "cavet":
        parse_cavet(lines, qr, out, [])
    elif kind == "cccd_front":
        parse_cccd(lines, None, qr, out, [])
    else:
        parse_cccd(None, lines, qr, out, [])
    got = {k: v.get("status") for k, v in out.items() if v.get("value")}
    exp = {"cavet": ["bks", "nhan_hieu", "so_khung", "so_may", "mau"], "cccd_front": ["cccd", "ho_ten"],
           "cccd_back": ["cccd", "ho_ten", "dia_chi", "ngay_cap"]}[kind]
    # Log an toàn: chỉ tên ô + trạng thái + chất lượng khung, KHÔNG có giá trị thật. ms = thời gian máy chủ xử lý (chưa gồm đường truyền).
    slog("PEEK", f"{_cip(request)} {kind} {img.shape[1]}x{img.shape[0]} {len(raw)//1024}KB ms={round((time.perf_counter()-t0)*1000)} "
         f"nét={round(sharp)} loá={glare:.3f} QR={'có' if qr else 'không'} dòng={len(lines)} "
         f"đọc={','.join(f'{k}:{v}' for k, v in got.items()) or '-'} thiếu={','.join(k for k in exp if k not in got) or '-'}")
    return {"sharp": round(sharp), "glare": round(glare, 3), "qr": bool(qr),
            "fields": {k: {"value": v.get("value", ""), "status": v.get("status")} for k, v in out.items() if v.get("value")}}


@app.post("/api/trace")
async def client_trace(request: Request, body: dict = Body(...)):
    """Điện thoại báo sự kiện luồng quét (chụp tay/tự chụp, dự phòng...) để đối chiếu với log PEEK. Chỉ nhận số liệu, không nhận giá trị."""
    ev = str(body.get("ev", ""))[:24]
    if ev not in ("snap", "fill", "fallback", "cam_open", "cam_close", "black_frame"):
        return {"ok": False}
    safe = " ".join(f"{k}={str(v)[:40]}" for k, v in body.items() if k != "ev" and re.fullmatch(r"[a-z_]{1,16}", str(k)) and not isinstance(v, (dict, list)))
    slog("APP", f"{_cip(request)} {ev} {safe}")
    return {"ok": True}


def _lan_ip() -> str:
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as so:
            so.connect(("10.255.255.255", 1))               # không gửi gói nào, chỉ để hệ điều hành chọn card mạng đang dùng
            return so.getsockname()[0]
    except OSError:
        return ""


def _tunnel_url() -> str:
    root = Path(__file__).resolve().parent.parent
    try:
        pid = int((root / ".run" / "tunnel.pid").read_text().strip())
        os.kill(pid, 0)                                      # tunnel còn sống?
        m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", (root / "logs" / "tunnel.log").read_text(errors="ignore"))
        return m.group(0) if m else ""
    except Exception:
        return ""


def _qr_uri(url: str) -> str:
    try:
        import segno
        return segno.make(url, error="l", boost_error=False).svg_data_uri(scale=6, border=2)
    except Exception:
        return ""


@app.get("/api/links")
def links(request: Request):
    """Địa chỉ để mở app trên điện thoại + mã QR (SVG), tính ở máy chủ nên luôn đúng với lần chạy hiện tại."""
    port = request.url.port or int(os.environ.get("PORT", "8000"))
    items = []
    ip = _lan_ip()
    if ip:
        u = f"{request.url.scheme}://{ip}:{port}"
        sec = request.url.scheme == "https"
        items.append({"label": "Cùng wifi", "note": ("Lần đầu điện thoại báo 'không an toàn': bấm Nâng cao → Tiếp tục. Camera dùng được." if sec else "Điện thoại phải cùng wifi với máy tính (chưa có camera trực tiếp)"), "url": u, "qr": _qr_uri(u)})
    t = _tunnel_url()
    if t:
        items.append({"label": "Link https", "note": "Dùng được camera, mở từ mọi nơi", "url": t, "qr": _qr_uri(t)})
    return {"items": items}


@app.get("/api/qr.png")
def qr_png(u: str = ""):
    """Ảnh QR (PNG) cho cửa sổ ScanApp trên máy tính (không hiểu SVG)."""
    import io
    import segno
    if not u or len(u) > 300:
        raise HTTPException(400, "thiếu địa chỉ")
    buf = io.BytesIO()
    segno.make(u, error="l", boost_error=False).save(buf, kind="png", scale=8, border=2)
    return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})


@app.get("/api/printer")
def printer_status():
    return printers.cached()


@app.post("/api/shutdown")
def shutdown(request: Request):
    """Dừng cả server + link https. Chỉ nhận từ chính máy này: chặn lệnh đi qua tunnel Cloudflare / proxy (có header chuyển tiếp)."""
    _need_local(request)
    run = ROOT / ".run"
    run.mkdir(exist_ok=True)
    (run / "stopped").write_text("1")          # để tác vụ tự cập nhật không bật lại
    if os.name == "nt":                        # Start-Process để script dừng không nằm trong cây tiến trình bị taskkill /T
        cmd = ["powershell", "-NoProfile", "-Command",
               f"Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','{ROOT / 'scripts' / 'stop.ps1'}'"]
        subprocess.Popen(cmd, creationflags=0x08000000)
    else:
        subprocess.Popen(["/bin/bash", str(ROOT / "scripts" / "stop.sh"), "--fast"], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {"ok": True}


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/manifest.webmanifest", include_in_schema=False)
def _manifest():
    return JSONResponse({"name": "Hợp đồng cầm đồ", "short_name": "Cầm đồ", "start_url": "/", "scope": "/", "display": "standalone",
        "background_color": "#F2F2F7", "theme_color": "#F2F2F7", "lang": "vi",
        "icons": [{"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]},
        media_type="application/manifest+json")


@app.get("/apple-touch-icon.png", include_in_schema=False)
def _touch_icon():
    return FileResponse(ROOT / "frontend" / "icons" / "icon-180.png", media_type="image/png")


class NoCacheStatic(StaticFiles):
    """File tĩnh luôn hỏi lại máy chủ (ETag) để sửa xong là trình duyệt/iPhone nhận bản mới, không giữ bản cũ."""
    async def get_response(self, path, scope):
        r = await super().get_response(path, scope)
        r.headers["Cache-Control"] = "no-cache"
        return r


app.mount("/static", NoCacheStatic(directory=ROOT / "frontend"), name="static")


def _asset_version() -> str:
    """Số phiên bản = thời điểm sửa mới nhất của file giao diện, để trình duyệt tải lại file tĩnh sau mỗi lần cập nhật."""
    return str(max((int(f.stat().st_mtime) for f in (ROOT / "frontend").rglob("*") if f.is_file()), default=0))


@app.get("/")
def index():
    html = (ROOT / "frontend" / "index.html").read_text("utf-8")
    html = re.sub(r'(/static/(?:css|js)/[\w-]+\.(?:css|js))', r'\1?v=' + _asset_version(), html)
    return Response(html, media_type="text/html; charset=utf-8", headers={"Cache-Control": "no-store"})
