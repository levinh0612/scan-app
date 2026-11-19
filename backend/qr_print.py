"""In mã QR ra terminal, nhiều mã xếp cạnh nhau:  python backend/qr_print.py "Nhãn=URL" ["Nhãn=URL" ...]
Lỗi (thiếu thư viện, terminal không hỗ trợ) thì im lặng bỏ qua — QR chỉ là tiện ích, không được làm hỏng run.sh/run.ps1."""
import sys

GAP = "   "


def render(url: str, version: int | None = None) -> list[str]:
    import segno
    m = [list(r) for r in segno.make(url, error="l", boost_error=False, version=version).matrix]
    w = len(m[0]) + 2                                   # viền 1 ô mỗi phía (đủ cho điện thoại quét)
    grid = [[False] * w] + [[False] + [bool(c) for c in r] + [False] for r in m] + [[False] * w]
    if len(grid) % 2:
        grid.append([False] * w)
    ch = {(False, False): "█", (False, True): "▀", (True, False): "▄", (True, True): " "}   # True = ô đen
    return ["".join(ch[(grid[y][x], grid[y + 1][x])] for x in range(w)) for y in range(0, len(grid), 2)]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    items = [a.split("=", 1) for a in sys.argv[1:] if "=" in a]
    import segno
    ver = max(segno.make(u, error="l", boost_error=False).version for _, u in items)   # mọi mã cùng một cỡ cho đều nhau
    cols = [(label, render(url, ver)) for label, url in items]
    h = max(len(c[1]) for c in cols)
    widths = [len(c[1][0]) for c in cols]
    print(GAP.join(label.center(w)[:w].ljust(w) for (label, _), w in zip(cols, widths)))
    for y in range(h):
        print(GAP.join((c[1][y] if y < len(c[1]) else " " * w) for c, w in zip(cols, widths)))


try:
    main()
except Exception:
    pass
