"""API hàng đợi lệnh in (RAM, dùng chung điện thoại + máy tính)."""
from __future__ import annotations

from fastapi import APIRouter
import io
import threading
from fastapi import HTTPException, Request
from fastapi.responses import Response

import layout
import printing
import render
from jobs import JobStore
from webutil import _authed, _body, _need_auth

router = APIRouter()


# ---------------- Hàng đợi lệnh in (RAM, dùng chung điện thoại + máy tính) ----------------
store = JobStore()


@router.get("/api/jobs")
def list_jobs(request: Request):
    jobs = store.list()
    if _authed(request):
        return jobs
    # Chưa nhập PIN (qua link công khai): che bớt biển số và tên khách
    mask = lambda t, n: (str(t)[:n] + "•••") if t else ""
    return [{**j, "bks": mask(j["bks"], 3), "chu": mask(j["chu"], 1)} for j in jobs]


@router.post("/api/jobs")
async def create_job(request: Request):
    d = await _body(request)
    try:
        return store.create(d.get("bks", ""), d.get("xe", ""), d.get("chu", ""), d.get("snapshot"),
                            d.get("status", "cho_in"))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/api/jobs/{jid}/snapshot")
def job_snapshot(jid: str, request: Request):
    _need_auth(request)
    snap = store.snapshot(jid)
    if snap is None:
        raise HTTPException(404, "Không tìm thấy lệnh in (có thể đã hết hạn)")
    return snap


@router.patch("/api/jobs/{jid}")
async def update_job(jid: str, request: Request):
    _need_auth(request)
    d = await _body(request)
    try:
        job = store.update(jid, d.get("status", ""))
    except ValueError as e:
        raise HTTPException(400, str(e))
    if job is None:
        raise HTTPException(404, "Không tìm thấy lệnh in")
    return job


@router.post("/api/jobs/{jid}/print")
def print_job(jid: str, request: Request):
    _need_auth(request)
    """Máy chủ tự gửi lệnh in tới máy in (không hộp thoại). Kết quả cập nhật dần vào trạng thái lệnh."""
    snap = store.snapshot(jid)
    if snap is None:
        raise HTTPException(404, "Không tìm thấy lệnh in (có thể đã hết hạn)")
    job = store.update(jid, "dang_in")
    threading.Thread(target=printing.run_job, args=(store, jid, snap), daemon=True).start()
    return job


@router.post("/api/jobs/{jid}/cancel")
def cancel_job(jid: str, request: Request):
    _need_auth(request)
    """Huỷ lệnh đang gửi tới máy in (chỉ khi còn trong hàng đợi máy in; đã ra khỏi hàng đợi thì không huỷ được)."""
    if store.snapshot(jid) is None:
        raise HTTPException(404, "Không tìm thấy lệnh in")
    printing.request_cancel(jid)
    return {"ok": True}


@router.get("/api/jobs/{jid}/preview.png")
def job_preview(jid: str, request: Request):
    _need_auth(request)
    """Ảnh đúng như sẽ in (nền trắng, chỉ phần điền vào) — để kiểm tra trước."""
    snap = store.snapshot(jid)
    if snap is None:
        raise HTTPException(404, "Không tìm thấy lệnh in")
    return _preview(snap)


def _preview(snap: dict) -> Response:
    tpl, cfg = layout.load_template(), printing.load_config()
    img, _ = render.render(layout.build_items(snap, tpl), tpl["page"], cfg["dx"], cfg["dy"])
    buf = io.BytesIO()
    render.save_png(img, buf)
    return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})


@router.delete("/api/jobs/{jid}")
def delete_job(jid: str, request: Request):
    _need_auth(request)
    if not store.delete(jid):
        raise HTTPException(404, "Không tìm thấy lệnh in")
    return {"ok": True}
