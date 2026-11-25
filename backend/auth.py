"""Mã PIN cho điện thoại (qua link công khai). Máy chủ (localhost) không cần PIN.

- PIN 4-6 chữ số, lưu dạng băm PBKDF2 (không lưu chữ thô) trong settings.
- Đăng nhập đúng → phiên (token ngẫu nhiên) tự khóa sau IDLE giây không dùng (mỗi lần gọi API gia hạn lại).
- Sai LIMIT lần liên tiếp → khóa mọi lần thử từ xa trong LOCK giây (đếm chung, vì link công khai khó phân biệt người dùng).
- Đặt/đổi PIN chỉ làm được trên máy chủ → đổi PIN là mọi phiên điện thoại bị đăng xuất.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import threading
import time

import settings

IDLE, LIMIT, LOCK = 300, 5, 300
_lock = threading.Lock()
_sessions: dict[str, float] = {}
_fails, _locked_until = 0, 0.0


def _hash(pin: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, 120_000).hex()


def pin_set() -> bool:
    return bool(settings.raw().get("pin_hash"))


def pin_len() -> int:
    n = settings.raw().get("pin_len", 0)
    return n if isinstance(n, int) and 4 <= n <= 6 else 0


def set_pin(pin: str) -> None:
    pin = str(pin or "").strip()
    if not re.fullmatch(r"\d{4,6}", pin):
        raise ValueError("PIN gồm 4 đến 6 chữ số")
    salt = secrets.token_bytes(16)
    d = settings.raw()
    d["pin_hash"], d["pin_salt"] = _hash(pin, salt), salt.hex()
    d["pin_len"] = len(pin)
    settings.write_raw(d)
    global _fails, _locked_until
    with _lock:
        _sessions.clear()
        _fails, _locked_until = 0, 0.0


def clear_pin() -> None:
    d = settings.raw()
    d.pop("pin_hash", None); d.pop("pin_salt", None); d.pop("pin_len", None)
    settings.write_raw(d)
    with _lock:
        _sessions.clear()


def locked_for(now: float | None = None) -> int:
    return max(int((_locked_until - (now or time.time())) + 0.999), 0)


def login(pin: str, now: float | None = None) -> str:
    """Trả token. Raise PermissionError (sai PIN) hoặc RuntimeError('lock:<giây>') khi đang khóa, ValueError khi chưa đặt PIN."""
    global _fails, _locked_until
    now = now or time.time()
    d = settings.raw()
    if not d.get("pin_hash"):
        raise ValueError("Chủ tiệm chưa đặt mã PIN")
    with _lock:
        if _locked_until > now:
            raise RuntimeError(f"lock:{locked_for(now)}")
        ok = hmac.compare_digest(_hash(str(pin or ""), bytes.fromhex(d["pin_salt"])), d["pin_hash"])
        if not ok:
            _fails += 1
            if _fails >= LIMIT:
                _fails, _locked_until = 0, now + LOCK
                raise RuntimeError(f"lock:{LOCK}")
            raise PermissionError(f"Sai PIN, còn {LIMIT - _fails} lần thử")
        _fails = 0
        tok = secrets.token_urlsafe(24)
        _sessions[tok] = now
        return tok


def valid(token: str | None, now: float | None = None) -> bool:
    """Token còn hạn → gia hạn thêm IDLE giây."""
    now = now or time.time()
    if not token:
        return False
    with _lock:
        for t in [t for t, at in _sessions.items() if now - at > IDLE]:
            del _sessions[t]
        if token in _sessions:
            _sessions[token] = now
            return True
        return False


def logout(token: str | None) -> None:
    with _lock:
        _sessions.pop(token or "", None)
