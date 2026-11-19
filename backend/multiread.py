"""Đọc cà vẹt nhiều lượt (mỗi lượt xử lý ảnh khác nhau) rồi bỏ phiếu từng ô; cắt ảnh nhỏ quanh chữ để người dùng đối chiếu.

Không phụ thuộc app.py (tránh import vòng): nhận hàm OCR/phân tích qua tham số.
"""
from __future__ import annotations

import base64
import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher

import cv2
import numpy as np


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def norm(v: str) -> str:
    """Khoá so sánh: bỏ dấu, dấu cách, '-', '.', ',' — 'Xanh, Xám' = 'xanh xam'."""
    return re.sub(r"[^a-z0-9]", "", _fold(v))


def vote(outs: list[dict]) -> dict:
    """Gộp kết quả nhiều lượt đọc. Mỗi ô: lấy giá trị nhiều lượt đọc trùng nhất (hoà → độ tin cậy cao hơn).
    Trả thêm `agree`/`of`/`src` (lượt đọc nào cho giá trị thắng). Lượt đọc bất đồng → luôn 'check' kèm giá trị khác."""
    n = len(outs)
    keys: list[str] = []
    for o in outs:
        keys += [k for k in o if k not in keys]
    res: dict = {}
    for k in keys:
        groups: dict[str, list[int]] = defaultdict(list)
        for i, o in enumerate(outs):
            v = (o.get(k) or {}).get("value")
            if v:
                groups[norm(v)].append(i)
        if not groups:
            res[k] = dict(outs[0].get(k) or {"value": "", "status": "missing"})
            continue
        conf = lambda i: (outs[i][k].get("conf") or 0)
        best = max(groups.values(), key=lambda g: (len(g), sum(conf(i) for i in g)))
        rep = max(best, key=conf)
        f = dict(outs[rep][k])
        f["agree"], f["of"], f["src"] = len(best), n, rep
        if len(best) < n:
            others = sorted({outs[i][k]["value"] for g in groups.values() if g is not best for i in g[:1]})
            f["status"] = "check" if f.get("status") != "missing" else "missing"
            why = f"{len(best)}/{n} lượt đọc trùng" + (f"; lượt khác ra: {', '.join(others)}" if others else "; lượt khác không đọc được")
            f["note"] = (f.get("note", "") + " — " if f.get("note") else "") + why
        elif n > 1:
            f["note"] = (f"{n}/{n} lượt đọc trùng. " + f.get("note", "")).strip()
        res[k] = f
    return res


def locate(lines, value: str, min_ratio: float = 0.6):
    """Dòng OCR có chữ giống `value` nhất → hộp (x0,y0,x1,y1) hoặc None."""
    want = norm(value)
    if not want:
        return None
    best, score = None, 0.0
    for ln in lines:
        box = getattr(ln, "box", None)
        t = norm(ln.text)
        if not box or not t:
            continue
        r = 1.0 if want in t else sum(b.size for b in SequenceMatcher(None, want, t, autojunk=False).get_matching_blocks()) / len(want)   # phần của `want` nằm trong dòng (dòng có thể kèm nhãn)
        if r > score:
            best, score = box, r
    return best if score >= min_ratio else None


def crop_data_url(img: np.ndarray, box, pad: int = 14, max_w: int = 420) -> str:
    h, w = img.shape[:2]
    x0, y0, x1, y1 = box
    x0, y0, x1, y1 = max(0, int(x0) - pad), max(0, int(y0) - pad), min(w, int(x1) + pad), min(h, int(y1) + pad)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return ""
    c = img[y0:y1, x0:x1]
    if c.shape[1] > max_w:
        c = cv2.resize(c, None, fx=max_w / c.shape[1], fy=max_w / c.shape[1], interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", c, [cv2.IMWRITE_JPEG_QUALITY, 75])
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode() if ok else ""


CROP_KEYS = ("bks", "nhan_hieu", "so_loai", "so_khung", "so_may", "mau")


def attach_crops(res: dict, lines_per_run: list, img: np.ndarray) -> None:
    for k in CROP_KEYS:
        f = res.get(k)
        if not f or not f.get("value"):
            continue
        box = locate(lines_per_run[f.get("src", 0)], f["value"]) or next(
            (b for b in (locate(ls, f["value"]) for ls in lines_per_run) if b), None)
        if box:
            f["crop"] = crop_data_url(img, box)
