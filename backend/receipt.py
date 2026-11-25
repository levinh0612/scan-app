"""Vẽ biên nhận (gia hạn / chuộc / thanh lý) và bản in thử ra ảnh A5 để máy chủ gửi thẳng máy in."""
from __future__ import annotations

from PIL import Image, ImageDraw

import layout
import render
from render import MM, _font, find_font

TITLES = {"gia_han": "BIÊN NHẬN GIA HẠN", "chuoc": "BIÊN NHẬN CHUỘC ĐỒ", "thanh_ly": "BIÊN BẢN THANH LÝ"}
CKEYS = ("ma", "ho_ten", "cccd", "sdt", "nhan_hieu", "so_loai", "mau", "bks", "so_khung", "so_may", "so_tien")
EKEYS = ("type", "at_vn", "days", "amount", "den_ngay_vn", "note")


def clean(d: dict, keys) -> dict:
    return {k: str(d.get(k) if d.get(k) is not None else "")[:200] for k in keys}


def rows(c: dict, e: dict) -> list[tuple[str, str]]:
    m = layout.money
    xe = " ".join(x for x in (c["nhan_hieu"], c["so_loai"], c["mau"]) if x)
    r = [("Khách hàng", c["ho_ten"]), ("CCCD", c["cccd"]), ("Điện thoại", c["sdt"]), ("Xe", xe), ("Biển số", c["bks"]),
         ("Số khung", c["so_khung"]), ("Số máy", c["so_may"]), ("Số tiền cầm gốc", m(c["so_tien"]) + " đồng" if c["so_tien"] else "")]
    if e["type"] == "gia_han":
        r += [("Gia hạn thêm", e["days"] + " ngày"), ("Phí gia hạn đã thu", m(e["amount"]) + " đồng"), ("Hạn mới", e["den_ngay_vn"])]
    elif e["type"] == "chuoc":
        r += [("Số tiền khách đã trả", m(e["amount"]) + " đồng"), ("Tình trạng", "Khách đã nhận lại xe")]
    r.append(("Ghi chú", e["note"]))
    return [(a, b) for a, b in r if b.strip()]


def render_receipt(c: dict, e: dict):
    page = layout.load_template()["page"]
    img = Image.new("L", (round(page["w"] * MM), round(page["h"] * MM)), 255)
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    fp = find_font()
    W, mx = img.width, round(16 * MM)
    big, mid, small = _font(fp, 17), _font(fp, 12), _font(fp, 10)
    title = TITLES.get(e["type"], "BIÊN NHẬN")
    y = round(26 * MM)
    d.text(((W - d.textlength(title, font=big)) / 2, y), title, font=big, fill=0, anchor="ls")
    y += round(9 * MM)
    sub = f"Hợp đồng số {c['ma']} · ngày {'/'.join(reversed(e['at_vn'][:10].split('-'))) if e['at_vn'] else ''}"
    d.text(((W - d.textlength(sub, font=mid)) / 2, y), sub, font=mid, fill=0, anchor="ls")
    y += round(14 * MM)
    for a, b in rows(c, e):
        d.text((mx, y), a, font=mid, fill=0, anchor="ls")
        d.text((mx + round(52 * MM), y), b, font=mid, fill=0, anchor="ls")
        y += round(8 * MM)
        d.line((mx, y - round(1.5 * MM), W - mx, y - round(1.5 * MM)), fill=170, width=1)
    y = max(y + round(18 * MM), round(155 * MM))
    for x0, lab in ((mx, "Khách hàng"), (W // 2 + round(4 * MM), "Người lập phiếu")):
        d.text((x0, y), lab, font=mid, fill=0, anchor="ls")
        d.text((x0, y + round(6 * MM)), "(ký, ghi rõ họ tên)", font=small, fill=0, anchor="ls")
    return img.point(lambda p: 255 if p > 127 else 0).convert("1")
