"""Từ dữ liệu hồ sơ (snapshot) + backend/template.json → danh sách chữ cần in (văn bản, x, y, rộng, cỡ chữ).
Chỉ in phần điền vào; chữ in sẵn của tờ mẫu KHÔNG in lại. Toạ độ tính bằng mm từ góc trên-trái tờ giấy."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

TEMPLATE = Path(__file__).with_name("template.json")
D = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def load_template(path: Path = TEMPLATE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def money(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def _read3(n: int, full: bool) -> str:
    t, c, d, o = n // 100, n // 10 % 10, n % 10, []
    if t or full:
        o.append(D[t] + " trăm")
    if c > 1:
        o.append(D[c] + " mươi")
    elif c == 1:
        o.append("mười")
    elif (t or full) and d:
        o.append("lẻ")
    if d:
        if c > 1 and d == 1:
            o.append("mốt")
        elif c >= 1 and d == 5:
            o.append("lăm")
        elif c > 1 and d == 4:
            o.append("tư")
        else:
            o.append(D[d])
    return " ".join(o)


def words(n: int) -> str:
    """Số tiền bằng chữ — cùng thuật toán với frontend (words trong index.html)."""
    if n == 0:
        return "Không đồng"
    units, groups = ["", " nghìn", " triệu", " tỷ"], []
    while n:
        groups.append(n % 1000)
        n //= 1000
    parts = [_read3(g, i != len(groups) - 1) + units[i % 4] for i, g in reversed(list(enumerate(groups))) if g]
    s = " ".join(parts).strip() + " đồng"
    return s[0].upper() + s[1:]


def _dmy(s: str) -> tuple[str, str, str]:
    p = (s or "").replace("-", "/").replace(".", "/").split("/")
    return tuple((p + ["", "", ""])[:3])  # type: ignore[return-value]


def _den_ngay(tu: str, so_ngay: str) -> str:
    try:
        d, m, y = (int(x) for x in _dmy(tu))
        return (datetime(y, m, d) + timedelta(days=int(so_ngay))).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return ""


def _int(s) -> int:
    try:
        return int(str(s).replace(".", "").replace(",", "").strip() or 0)
    except ValueError:
        return 0


def values(snap: dict) -> dict[str, str]:
    """Giá trị cần in cho từng ô của template."""
    g = lambda k: str(snap.get(k, "") or "").strip()  # noqa: E731
    n = _int(g("so_tien"))
    lines = [
        ", ".join(x for x in [
            f"Xe {' '.join(x for x in (g('nhan_hieu'), g('so_loai')) if x)}" if (g("nhan_hieu") or g("so_loai")) else "",
            f"màu {g('mau')}" if g("mau") else "", f"BKS {g('bks')}" if g("bks") else ""] if x),
        " — ".join(x for x in [f"Số khung: {g('so_khung')}" if g("so_khung") else "",
                               f"Số máy: {g('so_may')}" if g("so_may") else ""] if x),
    ]
    out = {"ho_ten": g("ho_ten"), "dia_chi": g("dia_chi"), "cccd": g("cccd"), "sdt": g("sdt"),
           "ke1": lines[0], "ke2": lines[1], "ke3": "",
           "le_phi": f"{money(_int(g('le_phi')))} đồng" if _int(g("le_phi")) else "",
           "chu": words(n) if n > 0 else "", "so": f"{money(n)} đồng" if n > 0 else ""}
    for prefix, src in (("ngay_cap", g("ngay_cap")), ("tu", g("tu_ngay")),
                        ("den", _den_ngay(g("tu_ngay"), g("so_ngay"))),
                        ("lap", g("ngay_lap") or datetime.now().strftime("%d/%m/%Y"))):
        for suffix, v in zip("dmy", _dmy(src)):
            out[f"{prefix}_{suffix}"] = v
    return out


def build_items(snap: dict, tpl: dict) -> list[dict]:
    vals, items = values(snap), []
    for key, f in tpl["fields"].items():
        text = vals.get(key, "")
        if not text:
            continue
        pre = f.get("prefix")
        if pre and text.startswith(pre) and len(text) > len(pre):
            text = text[len(pre):]          # '2026' → '6' vì giấy đã in sẵn '202'
        items.append({"key": key, "text": text, **{k: f[k] for k in ("x", "y", "w", "size")},
                      "align": f.get("align", "left")})
    return items
