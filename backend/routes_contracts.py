"""API PIN, cài đặt và hợp đồng đã lưu."""
from __future__ import annotations

from fastapi import APIRouter
import re
from datetime import datetime
from fastapi import Body, HTTPException, Request
from fastapi.responses import FileResponse, Response

import auth
import contracts
import images
import settings
from webutil import _authed, _backup_soon, _body, _guard, _is_local, _need_auth, _need_local

router = APIRouter()


@router.get("/api/auth/status")
def auth_status(request: Request):
    return {"local": _is_local(request), "authed": _authed(request), "pin_set": auth.pin_set(), "pin_len": auth.pin_len(), "locked_for": auth.locked_for(), "idle": auth.IDLE}


@router.post("/api/auth/login")
async def auth_login(request: Request):
    d = await _body(request)
    try:
        return {"token": auth.login(str(d.get("pin") or "")), "idle": auth.IDLE}
    except PermissionError as e:
        raise HTTPException(401, str(e))
    except RuntimeError as e:
        sec = int(str(e).split(":")[1])
        raise HTTPException(429, f"Nhập sai quá nhiều lần. Thử lại sau {sec // 60}:{sec % 60:02d}", headers={"Retry-After": str(sec)})
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/api/auth/logout")
def auth_logout(request: Request):
    auth.logout(request.headers.get("x-session"))
    return {"ok": True}


@router.post("/api/auth/pin")
async def auth_set_pin(request: Request):
    _need_local(request)
    d = await _body(request)
    _guard(auth.set_pin, str(d.get("pin") or ""))
    return {"ok": True}


@router.get("/api/settings")
def settings_get(request: Request):
    s = settings.get()
    if not _is_local(request):                         # điện thoại chỉ cần lệ phí/ngày mặc định để điền form
        return {k: s[k] for k in settings.PUBLIC if k != "anh_giu_ngay"}
    return {**s, "pin_set": auth.pin_set(), "anh": images.usage(), "sao_luu": contracts.last_backup(), "sao_luu_ngoai": contracts.offsite_status()}


@router.post("/api/settings")
async def settings_set(request: Request):
    _need_local(request)
    return _guard(settings.save, await _body(request))


@router.post("/api/contracts/check")
async def contracts_check(request: Request):
    d = await _body(request)
    return {"warnings": contracts.check({k: str(v)[:300] for k, v in d.items() if isinstance(v, (str, int))}, _is_local(request))}


@router.post("/api/contracts")
async def contracts_create(request: Request):
    d = await _body(request)
    local = _is_local(request)
    r = _guard(contracts.create, {k: str(v)[:300] for k, v in d.items() if isinstance(v, (str, int))}, None, local)
    if not r.get("duplicate"):
        _backup_soon()
    if not local:        # qua link công khai: chỉ trả mã/hạn, không trả tên/CCCD (hợp đồng trả về có thể là của khách khác khi bấm trùng)
        r["contract"] = {k: r["contract"][k] for k in ("id", "ma", "den_ngay_vn", "hien_thi")}
    return r


@router.get("/api/contracts")
def contracts_list(request: Request, q: str = "", status: str = "", limit: int = 100, offset: int = 0):
    _need_auth(request)
    return contracts.search(q[:80], status, limit, offset)


@router.get("/api/contracts/stats")
def contracts_stats(request: Request):
    _need_auth(request)
    return contracts.stats(remote=not _is_local(request))        # điện thoại: chỉ số lượng, không có tiền


@router.get("/api/contracts/report")
def contracts_report(request: Request, frm: str = "", to: str = ""):
    _need_local(request)                                         # tiền vốn/lợi nhuận: chỉ xem trên máy tính ở tiệm
    return _guard(contracts.report, frm, to)


@router.get("/api/contracts/backups")
def contracts_backups(request: Request):
    _need_local(request)
    return {"items": contracts.list_backups(), "ngoai": contracts.offsite_status()}


@router.post("/api/contracts/restore")
async def contracts_restore(request: Request):
    _need_local(request)
    d = await _body(request)
    return _guard(contracts.restore, str(d.get("name") or ""))


@router.post("/api/contracts/offsite")
def contracts_offsite(request: Request, body: dict = Body(...)):
    _need_local(request)
    try:
        return contracts.set_offsite(str(body.get("path", "")))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/api/contracts/backup")
def contracts_backup(request: Request):
    _need_local(request)
    p = contracts.backup()
    return {"file": p.name if p else "", "sao_luu": contracts.last_backup()}


@router.get("/api/contracts/backup/download")
def contracts_backup_download(request: Request):
    """Tạo bản sao lưu mới rồi cho tải về máy (dùng khi không có Drive/OneDrive/USB: lưu tay vào USB, gửi email, Zalo...)."""
    _need_local(request)
    p = contracts.backup()
    if not p:
        raise HTTPException(500, "Không tạo được bản sao lưu")
    return FileResponse(p, media_type="application/octet-stream", filename=p.name, headers={"Cache-Control": "no-store"})


@router.get("/api/contracts/export.csv")
def contracts_export(request: Request):
    _need_local(request)
    return Response(contracts.export_csv(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=hop-dong.csv"})


@router.get("/api/contracts/{cid}")
def contracts_detail(cid: int, request: Request):
    _need_auth(request)
    d = _guard(contracts.detail, cid)
    d["anh"] = images.available(d["contract"]["ma"])
    return d


# Ảnh: máy chủ / đã nhập PIN được xem. Tải ảnh lên: máy chủ, đã nhập PIN, hoặc điện thoại vừa lập hợp đồng đó (≤ 30 phút, chưa có ảnh loại này).
@router.post("/api/contracts/{cid}/anh/{kind}")
async def contracts_image_put(cid: int, kind: str, request: Request):
    c = _guard(contracts.detail, cid)["contract"]
    if not _authed(request):
        age = (datetime.now() - datetime.fromisoformat(c["created_at"])).total_seconds()
        if age > 1800 or images.path(c["ma"], kind):
            raise HTTPException(401, "Cần nhập mã PIN")
    data = await request.body()
    if not data or len(data) > 15 * 1024 * 1024:
        raise HTTPException(400, "Ảnh rỗng hoặc quá lớn")
    return {"ok": True, "bytes": _guard(images.save, c["ma"], kind, data)}


@router.get("/api/contracts/{cid}/anh/{kind}")
def contracts_image_get(cid: int, kind: str, request: Request):
    _need_auth(request)
    p = images.path(_guard(contracts.detail, cid)["contract"]["ma"], kind)
    if not p:
        raise HTTPException(404, "Không có ảnh")
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"})


@router.post("/api/contracts/{cid}/{action}")
async def contracts_action(cid: int, action: str, request: Request):
    if action in ("renew", "chuoc", "thanh_ly", "note"):
        _need_auth(request)                                      # điện thoại sau PIN được gia hạn/chuộc/thanh lý/ghi chú
    else:
        _need_local(request)                                     # sửa/hủy/mở lại: chỉ máy tính ở tiệm
    d = await _body(request)
    num = lambda k: int(re.sub(r"\D", "", str(d.get(k) or "")) or 0)
    note = str(d.get("note") or "")
    if action == "renew":
        r = _guard(contracts.renew, cid, num("days"), num("fee"), note)
    elif action in ("chuoc", "thanh_ly"):
        r = _guard(contracts.close, cid, action, num("amount"), note)
    elif action == "note":
        return _guard(contracts.set_note, cid, note)
    elif action == "reopen":
        r = _guard(contracts.reopen, cid)
    elif action == "sua":
        r = _guard(contracts.update, cid, {k: v for k, v in d.items() if isinstance(v, (str, int))})
    elif action == "huy":
        r = _guard(contracts.cancel, cid, str(d.get("reason") or ""))
    elif action == "xoa":
        return _delete_hard(cid, str(d.get("confirm") or ""))
    else:
        raise HTTPException(404, "Thao tác không có")
    _backup_soon()
    return r


def _delete_hard(cid: int, confirm: str) -> dict:
    """Xóa hẳn hồ sơ (thử nghiệm): phải gửi đúng mã hợp đồng để xác nhận, và luôn sao lưu trước khi xóa."""
    ma = _guard(contracts.detail, cid)["contract"]["ma"]
    if confirm != ma:
        raise HTTPException(400, "Mã xác nhận không khớp")
    contracts.backup()
    _guard(contracts.delete_hard, cid)
    images.remove(ma)
    return {"ok": True, "ma": ma}
