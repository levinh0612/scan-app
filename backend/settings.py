"""Cài đặt của tiệm (data/settings.json): lệ phí/kỳ mặc định, số ngày mỗi kỳ, thời gian giữ ảnh, mã PIN (đã băm)."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = Path(os.environ.get("SCAN_SETTINGS") or ROOT / "data" / "settings.json")
_lock = threading.Lock()
DEFAULTS = {"so_ngay_ky": 30, "le_phi_ky": 0, "anh_giu_ngay": 90}
PUBLIC = ("so_ngay_ky", "le_phi_ky", "anh_giu_ngay")        # hiển thị được cho điện thoại (không có PIN)
LIMITS = {"so_ngay_ky": (1, 365), "le_phi_ky": (0, 10**9), "anh_giu_ngay": (7, 3650)}


def _load() -> dict:
    try:
        d = json.loads(PATH.read_text("utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def get() -> dict:
    d = _load()
    return {k: d.get(k, v) for k, v in DEFAULTS.items()}


def save(changes: dict) -> dict:
    """Chỉ nhận các khoá hợp lệ, ép về số nguyên trong giới hạn."""
    with _lock:
        d = _load()
        for k, (lo, hi) in LIMITS.items():
            if k in changes:
                try:
                    v = int(str(changes[k]).replace(".", "").replace(",", "").strip())
                except ValueError:
                    raise ValueError("Giá trị không hợp lệ")
                if not lo <= v <= hi:
                    raise ValueError(f"Giá trị phải từ {lo} đến {hi}")
                d[k] = v
        PATH.parent.mkdir(parents=True, exist_ok=True)
        PATH.write_text(json.dumps(d), "utf-8")
    return get()


def raw() -> dict:
    return _load()


def write_raw(d: dict) -> None:
    with _lock:
        PATH.parent.mkdir(parents=True, exist_ok=True)
        PATH.write_text(json.dumps(d), "utf-8")
