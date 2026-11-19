"""Vẽ icon ScanApp (thẻ giấy tờ + khung quét) → assets/scanapp.png (1024) và scanapp.ico (đa kích thước).
Chạy:  .venv/bin/python assets/make_icon.py   (macOS: make-mac-app.sh tự tạo .icns từ PNG)"""
from pathlib import Path
from PIL import Image, ImageDraw

S = 1024
OUT = Path(__file__).resolve().parent


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw() -> Image.Image:
    # nền: bo góc kiểu Apple, gradient xanh hệ thống
    bg = Image.new("RGBA", (S, S))
    px = bg.load()
    top, bot = (64, 156, 255), (0, 82, 204)
    for y in range(S):
        c = lerp(top, bot, y / S)
        for x in range(S):
            px[x, y] = (*c, 255)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((40, 40, S - 40, S - 40), radius=225, fill=255)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    img.paste(bg, (0, 0), mask)
    d = ImageDraw.Draw(img)
    # thẻ giấy tờ (trắng) với ảnh chân dung + dòng chữ
    d.rounded_rectangle((200, 300, 824, 724), radius=56, fill=(255, 255, 255, 255))
    d.ellipse((260, 400, 380, 520), fill=(190, 205, 225, 255))
    d.rounded_rectangle((260, 540, 380, 640), radius=40, fill=(190, 205, 225, 255))
    for i, w in enumerate((330, 270, 300)):
        d.rounded_rectangle((430, 410 + i * 70, 430 + w, 440 + i * 70), radius=15, fill=(205, 214, 228, 255))
    # khung quét 4 góc (cam) bao quanh thẻ
    c, t, L = (255, 159, 10, 255), 34, 130
    x0, y0, x1, y1 = 150, 250, 874, 774
    for (ax, ay, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.rounded_rectangle((min(ax, ax + sx * L), min(ay, ay + sy * t), max(ax, ax + sx * L), max(ay, ay + sy * t)), radius=t // 2, fill=c)
        d.rounded_rectangle((min(ax, ax + sx * t), min(ay, ay + sy * L), max(ax, ax + sx * t), max(ay, ay + sy * L)), radius=t // 2, fill=c)
    # tia quét
    d.rounded_rectangle((170, 500, 854, 524), radius=12, fill=(255, 159, 10, 235))
    return img


if __name__ == "__main__":
    im = draw()
    im.save(OUT / "scanapp.png")
    im.save(OUT / "scanapp.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("OK:", OUT / "scanapp.png", OUT / "scanapp.ico")
