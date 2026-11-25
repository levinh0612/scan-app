"""Ảnh giấy tờ đã quét: lưu thành FILE trong data/anh/<mã hợp đồng>/ (không nhét vào database).

Ảnh được thu nhỏ (cạnh dài ≤ 1280 px) và nén JPEG ~70% → khoảng 150–250 KB/ảnh. Hợp đồng đã chuộc/thanh lý/hủy:
ảnh tự xóa sau N ngày (cài đặt 'anh_giu_ngay', mặc định 90). Ảnh chứa CCCD nên không giữ mãi.
"""
from __future__ import annotations

import os
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = Path(os.environ.get("SCAN_IMAGES") or ROOT / "data" / "anh")
KINDS = {"cccd": "cccd-sau.jpg", "cavet": "ca-vet.jpg"}
MAX_EDGE, QUALITY = 1280, 70


def _dir(ma: str) -> Path:
    if not re.fullmatch(r"\d{8}-\d{4}", ma or ""):
        raise ValueError("Mã hợp đồng không hợp lệ")
    return IMG_DIR / ma


def save(ma: str, kind: str, data: bytes) -> int:
    """Nén và lưu ảnh. Trả số byte đã ghi."""
    if kind not in KINDS:
        raise ValueError("Loại ảnh không hợp lệ")
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Không đọc được ảnh")
    h, w = img.shape[:2]
    s = MAX_EDGE / max(h, w)
    if s < 1:
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, QUALITY])
    if not ok:
        raise ValueError("Không nén được ảnh")
    d = _dir(ma)
    d.mkdir(parents=True, exist_ok=True)
    (d / KINDS[kind]).write_bytes(buf.tobytes())
    return len(buf)


def path(ma: str, kind: str) -> Path | None:
    if kind not in KINDS:
        return None
    p = _dir(ma) / KINDS[kind]
    return p if p.is_file() else None


def remove(ma: str) -> None:
    """Xóa cả thư mục ảnh của hợp đồng."""
    shutil.rmtree(_dir(ma), ignore_errors=True)


def available(ma: str) -> list[str]:
    return [k for k in KINDS if path(ma, k)]


def usage() -> dict:
    n = size = 0
    if IMG_DIR.is_dir():
        for f in IMG_DIR.rglob("*.jpg"):
            n += 1; size += f.stat().st_size
    return {"so_anh": n, "mb": round(size / 1048576, 1), "thu_muc": str(IMG_DIR)}


def cleanup(closed: list[tuple[str, str]], keep_days: int, now: datetime | None = None) -> int:
    """closed = [(mã HĐ, closed_at ISO)] của hợp đồng đã đóng/hủy. Xóa thư mục ảnh quá keep_days ngày. Trả số thư mục đã xóa."""
    now = now or datetime.now()
    removed = 0
    for ma, at in closed:
        try:
            if not at or datetime.fromisoformat(at) > now - timedelta(days=keep_days):
                continue
            d = _dir(ma)
        except ValueError:
            continue
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            removed += 1
    return removed
