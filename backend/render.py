"""Vẽ trang A5 (chỉ phần điền vào, nền trắng) ra ảnh đen/trắng 300dpi để gửi cho mọi loại máy in có driver.
Ảnh 1-bit, không khử răng cưa: máy kim/phun/laser đều in nét, không bị rỗ vì hoà màu xám."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DPI = 300
MM = DPI / 25.4
MIN_PT = 7.0
FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def find_font() -> str:
    for p in FONTS:
        if Path(p).exists():
            return p
    raise RuntimeError("Không tìm thấy font Arial/Liberation/DejaVu để vẽ chữ tiếng Việt")


def _font(path: str, pt: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, max(1, round(pt * DPI / 72)))


def render(items: list[dict], page: dict, dx: float = 0.0, dy: float = 0.0, font_path: str | None = None):
    """→ (ảnh PIL mode '1', danh sách cảnh báo). dx, dy (mm): dịch cả trang để bù lệch cơ học của máy in."""
    font_path = font_path or find_font()
    img = Image.new("L", (round(page["w"] * MM), round(page["h"] * MM)), 255)
    d, warns = ImageDraw.Draw(img), []
    d.fontmode = "1"
    for it in items:
        pt, text, width = float(it["size"]), it["text"], it["w"] * MM
        f = _font(font_path, pt)
        while d.textlength(text, font=f) > width and pt > MIN_PT:
            pt -= 0.5
            f = _font(font_path, pt)
        if d.textlength(text, font=f) > width:
            warns.append(f"{it['key']}: chữ dài hơn ô, đã thu nhỏ hết cỡ vẫn tràn")
        tw = d.textlength(text, font=f)
        x = it["x"] * MM + (0 if it["align"] == "left" else (width - tw) / (2 if it["align"] == "center" else 1))
        d.text((x + dx * MM, (it["y"] + dy) * MM), text, font=f, fill=0, anchor="ls")
    return img.point(lambda p: 255 if p > 127 else 0).convert("1"), warns


def save_png(img, target) -> None:
    img.save(target, format="PNG", dpi=(DPI, DPI))


if __name__ == "__main__":      # python backend/render.py out.png  → bản in thử bằng dữ liệu mẫu
    from layout import build_items, load_template
    t = load_template()
    snap = dict(ho_ten="NGUYEN VAN A", dia_chi="123 Đường ABC, P. 1, TP Phan Rang", cccd="058200000000", sdt="0900000000",
                ngay_cap="15/03/2021", nhan_hieu="HONDA", so_loai="VISION", mau="Đỏ", bks="85B1-123.45",
                so_khung="RLHJK1403PZ123456", so_may="JK14E1234567", le_phi="50000", so_tien="5000000",
                so_ngay="30", tu_ngay="19/11/2026", ngay_lap="19/11/2026")
    im, w = render(build_items(snap, t), t["page"])
    save_png(im, Path(sys.argv[1]))
    print(im.size, w)
