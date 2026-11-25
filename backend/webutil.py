"""Hàm dùng chung cho các router: kiểm tra máy chủ/PIN, đọc body, bắt lỗi nghiệp vụ."""
from __future__ import annotations
import threading
from fastapi import HTTPException, Request

import auth
import contracts


def _is_local(request: Request) -> bool:
    """Request đến thẳng từ chính máy chủ (không qua tunnel Cloudflare / proxy có header chuyển tiếp)."""
    proxied = any(h in request.headers for h in ("cf-connecting-ip", "x-forwarded-for", "cf-ray", "forwarded"))
    return not proxied and (request.client.host if request.client else "") in ("127.0.0.1", "::1")


def _need_local(request: Request) -> None:
    if not _is_local(request):
        raise HTTPException(403, "Chỉ xem/sửa được hợp đồng trên máy chủ (không qua link công khai)")


async def _body(request: Request) -> dict:
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(400, "Dữ liệu gửi lên không hợp lệ")
    if not isinstance(data, dict):
        raise HTTPException(400, "Dữ liệu gửi lên không hợp lệ")
    return data


# ---------- Hợp đồng đã lưu: cảnh báo trùng, tra cứu, gia hạn, chuộc ----------
# Điện thoại (qua tunnel) chỉ được kiểm tra trùng + lưu; xem danh sách/chi tiết/gia hạn/chuộc/xuất file chỉ trên máy chủ.
def _guard(fn, *a, **k):
    try:
        return fn(*a, **k)
    except KeyError as e:
        raise HTTPException(404, str(e.args[0]))
    except ValueError as e:
        raise HTTPException(400, str(e))


def _backup_soon() -> None:
    """Sao lưu ngay sau mỗi thay đổi (nền, không làm chậm thao tác)."""
    threading.Thread(target=lambda: contracts.backup(), daemon=True).start()


# ---------- Mã PIN: điện thoại (qua link công khai) phải nhập PIN mới xem/thao tác hợp đồng ----------
def _authed(request: Request) -> bool:
    return _is_local(request) or auth.valid(request.headers.get("x-session"))


def _need_auth(request: Request) -> None:
    if not _authed(request):
        raise HTTPException(401, "Cần nhập mã PIN")
