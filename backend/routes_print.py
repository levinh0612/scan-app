"""In biên nhận và in thử từ máy chủ (không dùng hộp thoại in của trình duyệt)."""
from __future__ import annotations

import io
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

import layout
import printing
import receipt
import render
from webutil import _body, _need_auth

router = APIRouter()

SAMPLE = dict(ho_ten="NGUYEN VAN A", dia_chi="123 Đường ABC, P. 1, TP Phan Rang", cccd="058200000000", sdt="0900000000",
              ngay_cap="15/03/2021", nhan_hieu="HONDA", so_loai="VISION", mau="Đỏ", bks="85B1-123.45",
              so_khung="RLHJK1403PZ123456", so_may="JK14E1234567", le_phi="50000", so_tien="5000000",
              so_ngay="30", tu_ngay="19/11/2026", ngay_lap="19/11/2026")


def _png(img) -> Response:
    buf = io.BytesIO()
    render.save_png(img, buf)
    return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})


def _test_img():
    cfg, tpl = printing.load_config(), layout.load_template()
    img, _ = render.render(layout.build_items(SAMPLE, tpl), tpl["page"], cfg["dx"], cfg["dy"])
    return img


async def _receipt_img(request: Request):
    d = await _body(request)
    c, e = receipt.clean(d.get("c") or {}, receipt.CKEYS), receipt.clean(d.get("e") or {}, receipt.EKEYS)
    if e["type"] not in receipt.TITLES:
        raise HTTPException(400, "Loại biên nhận không hợp lệ")
    return receipt.render_receipt(c, e)


def _send(img, tag: str) -> dict:
    try:
        printer = printing.print_image(img, f"{tag}{int(time.time())}")
    except printing.PrintError as ex:
        raise HTTPException(400, str(ex))
    return {"ok": True, "printer": printer}


@router.get("/api/print/test.png")
def test_png(request: Request):
    _need_auth(request)
    return _png(_test_img())


@router.post("/api/print/test")
def test_print(request: Request):
    _need_auth(request)
    return _send(_test_img(), "T")


@router.post("/api/print/receipt.png")
async def receipt_png(request: Request):
    _need_auth(request)
    return _png(await _receipt_img(request))


@router.post("/api/print/receipt")
async def receipt_print(request: Request):
    _need_auth(request)
    return _send(await _receipt_img(request), "R")
