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


def _merge_truncated(groups: dict[str, list[int]]) -> None:
    """Tên màu hay bị OCR cụt chữ cuối ('Xanh Xám' thay vì 'Xanh Xám Đen'): lượt đọc cụt tính là phiếu ủng hộ cho lượt đọc đầy đủ hơn
    (OCR hay bỏ chữ cuối, hiếm khi bịa thêm tên màu). Chỉ gộp khi chuỗi ngắn là phần đầu của chuỗi dài."""
    for short in sorted(groups, key=len):
        longer = [g for g in groups if len(g) > len(short) and g.startswith(short)]
        if longer and short in groups:
            tgt = max(longer, key=lambda g: len(groups[g]))
            groups[tgt] += groups.pop(short)


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
        if k == "mau":
            _merge_truncated(groups)
        if not groups:
            res[k] = dict(outs[0].get(k) or {"value": "", "status": "missing"})
            continue
        conf = lambda i: (outs[i][k].get("conf") or 0)
        best = max(groups.values(), key=lambda g: (len(g), 0 in g, sum(conf(i) for i in g)))   # hoà số phiếu → nghiêng về lượt 0 (cách xử lý đã được đo là ổn định nhất), không tin độ tin cậy giữa các lượt
        rep = max(best, key=conf)
        f = dict(outs[rep][k])
        f["agree"], f["of"], f["src"] = len(best), n, rep
        if len(best) < n:
            others = sorted({outs[i][k]["value"] for g in groups.values() if g is not best for i in g[:1]})
            f["status"] = "check" if f.get("status") != "missing" else "missing"
            why = f"{len(best)}/{n} lượt đọc trùng" + (f"; lượt khác ra: {', '.join(others)}" if others else "; lượt khác không đọc được")
            f["note"] = (f.get("note", "") + " — " if f.get("note") else "") + why
        res[k] = f
    return res


def locate(lines, value: str, min_ratio: float = 0.75):
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
        # đoạn liền dài nhất của `want` nằm trong dòng (dòng có thể kèm nhãn). Chỉ tính đoạn LIỀN: cộng các mảnh rời sẽ khớp nhầm dòng khác ('HONDA' ~ địa chỉ)
        r = 1.0 if want in t else SequenceMatcher(None, want, t, autojunk=False).find_longest_match(0, len(want), 0, len(t)).size / len(want)
        if r > score:
            best, score = box, r
    return best if score >= min_ratio else None


def crop_data_url(img: np.ndarray, box, pad: int = 14, max_w: int = 420) -> str:
    h, w = img.shape[:2]
    x0, y0, x1, y1 = box
    py = 3      # chừa ít phía trên/dưới để không lòi dòng chữ kế bên
    x0, y0, x1, y1 = max(0, int(x0) - pad), max(0, int(y0) - py), min(w, int(x1) + pad), min(h, int(y1) + py)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return ""
    c = img[y0:y1, x0:x1]
    if c.shape[1] > max_w:
        c = cv2.resize(c, None, fx=max_w / c.shape[1], fy=max_w / c.shape[1], interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", c, [cv2.IMWRITE_JPEG_QUALITY, 75])
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode() if ok else ""


LABEL_RX = {"mau": r"mau son|colou?r", "so_may": r"so may|engine", "so_khung": r"so khung|chassis",
            "nhan_hieu": r"nhan hieu|brand", "so_loai": r"so loai|model", "bks": r"bien so|plate"}


def locate_label(lines, key: str):
    """Dự phòng: giá trị OCR đọc lệch quá nên không khớp chữ → lấy dòng chứa NHÃN của ô đó."""
    rx = re.compile(LABEL_RX.get(key, "$^"))
    for ln in lines:
        if getattr(ln, "box", None) and rx.search(_fold(ln.text)):
            return ln.box
    return None


CROP_KEYS = ("bks", "nhan_hieu", "so_loai", "so_khung", "so_may", "mau")


def attach_crops(res: dict, lines_per_run: list, img: np.ndarray) -> None:
    for k in CROP_KEYS:
        f = res.get(k)
        if not f or not f.get("value"):
            continue
        box = locate(lines_per_run[f.get("src", 0)], f["value"]) or next(
            (b for b in (locate(ls, f["value"]) for ls in lines_per_run) if b), None) or locate_label(lines_per_run[f.get("src", 0)], k)
        if box and k in ("nhan_hieu", "so_loai"):   # ô 'Nhãn hiệu - loại': hiện cả 2 dòng (hãng + số loại) cho cùng một ảnh, đủ to để đối chiếu
            other = "so_loai" if k == "nhan_hieu" else "nhan_hieu"
            ov = res.get(other, {}).get("value")
            lb = locate(lines_per_run[f.get("src", 0)], ov) if ov else None
            if lb and abs((lb[1] + lb[3]) - (box[1] + box[3])) / 2 < 4 * max(box[3] - box[1], 1):
                box = (min(box[0], lb[0]), min(box[1], lb[1]), max(box[2], lb[2]), max(box[3], lb[3]))
            hh = box[3] - box[1]
            box = (box[0], box[1] - 0.05 * hh, box[2], box[3] + 1.15 * hh)   # lấy thêm 1 dòng dưới: ảnh cao 2 dòng, hiện to dễ đọc
        if box:
            f["crop"] = crop_data_url(img, box, max_w=640 if k in ("nhan_hieu", "so_loai") else 420)
