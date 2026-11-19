"""Kiểm tra chéo & chuẩn hoá dữ liệu giấy tờ. Thuần Python, không phụ thuộc thư viện ngoài."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

# Mã tỉnh/thành trong số CCCD (3 chữ số đầu)
PROVINCE_CODES = {
    "001", "002", "004", "006", "008", "010", "011", "012", "014", "015", "017", "019", "020",
    "022", "024", "025", "026", "027", "030", "031", "033", "034", "035", "036", "037", "038",
    "040", "042", "044", "045", "046", "048", "049", "051", "052", "054", "056", "058", "060",
    "062", "064", "066", "067", "068", "070", "072", "074", "075", "077", "079", "080", "082",
    "083", "084", "086", "087", "089", "091", "092", "093", "094", "095", "096",
}


def check_cccd(number: str, dob_year: int | None = None, gender: str | None = None) -> list[str]:
    """Trả về danh sách lỗi (rỗng = hợp lệ). Cấu trúc: 3 số tỉnh + 1 số giới tính/thế kỷ + 2 số năm sinh + 6 số ngẫu nhiên."""
    errs: list[str] = []
    n = re.sub(r"\s", "", number or "")
    if not re.fullmatch(r"\d{12}", n):
        return ["Số CCCD phải đủ 12 chữ số"]
    if n[:3] not in PROVINCE_CODES:
        errs.append(f"Mã tỉnh {n[:3]} không hợp lệ")
    g = int(n[3])  # 0/1: 1900s, 2/3: 2000s, ... (chẵn = nam, lẻ = nữ)
    century = 1900 + (g // 2) * 100
    year = century + int(n[4:6])
    if dob_year and year != dob_year:
        errs.append(f"Năm sinh trong số CCCD ({year}) không khớp ngày sinh ({dob_year})")
    if gender:
        is_male = g % 2 == 0
        if (gender.lower().startswith("nam")) != is_male:
            errs.append("Giới tính không khớp với số CCCD")
    return errs


def normalize_plate(raw: str) -> str:
    """'85b1-123.45' -> '85B1-123.45'. Giữ nguyên dấu gạch/chấm hợp lệ, sửa nhầm lẫn ký tự thường gặp."""
    s = re.sub(r"[^0-9A-ZĐ.\-]", "", (raw or "").upper())
    return s


def check_plate(plate: str) -> bool:
    # 2 số tỉnh + 1-2 ký tự series (chữ[+số]) + gạch + 4-5 số (có thể có dấu chấm)
    return bool(re.fullmatch(r"\d{2}-?[A-ZĐ]{1,2}\d?-?\d{3}\.?\d{1,2}", normalize_plate(plate)))


def fix_vin_like(raw: str) -> str:
    """Số khung/số máy: chỉ chữ+số. Chuẩn hoá hoa; không tự đoán O/0 (để người dùng xác nhận)."""
    return re.sub(r"[^0-9A-Z\-]", "", (raw or "").upper())


def parse_cccd_qr(text: str) -> dict | None:
    """QR thẻ CCCD gắn chip: số|CMND cũ|họ tên|ngày sinh ddmmyyyy|giới tính|địa chỉ|ngày cấp ddmmyyyy.
    Thẻ căn cước mới có thể chỉ chứa số định danh -> trả về dict chỉ có 'cccd'."""
    t = (text or "").strip()
    if re.fullmatch(r"\d{12}", t):
        return {"cccd": t}
    parts = t.split("|")
    if len(parts) >= 7 and re.fullmatch(r"\d{12}", parts[0]):
        def d(s: str) -> str:
            return f"{s[:2]}/{s[2:4]}/{s[4:]}" if re.fullmatch(r"\d{8}", s) else ""
        return {
            "cccd": parts[0], "ho_ten": parts[2], "ngay_sinh": d(parts[3]),
            "gioi_tinh": parts[4], "dia_chi": parts[5], "ngay_cap": d(parts[6]),
        }
    return None


# ---------- Đọc số tiền thành chữ ----------
_DIGITS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _read3(n: int, full: bool) -> str:
    """Đọc nhóm 3 chữ số. full=True: có đọc 'không trăm' (khi không phải nhóm đầu)."""
    tram, chuc, dv = n // 100, (n // 10) % 10, n % 10
    out: list[str] = []
    if tram or full:
        out.append(f"{_DIGITS[tram]} trăm")
    if chuc > 1:
        out.append(f"{_DIGITS[chuc]} mươi")
    elif chuc == 1:
        out.append("mười")
    elif (tram or full) and dv:
        out.append("lẻ")
    if dv:
        if chuc > 1 and dv == 1:
            out.append("mốt")
        elif chuc >= 1 and dv == 5:
            out.append("lăm")
        elif chuc > 1 and dv == 4:
            out.append("tư")
        else:
            out.append(_DIGITS[dv])
    return " ".join(out)


def money_to_words(n: int) -> str:
    """5000000 -> 'Năm triệu đồng'; 12500000 -> 'Mười hai triệu năm trăm nghìn đồng'."""
    if n < 0:
        raise ValueError("Số tiền không được âm")
    if n == 0:
        return "Không đồng"
    units = ["", " nghìn", " triệu", " tỷ"]
    groups: list[int] = []
    while n:
        groups.append(n % 1000)
        n //= 1000
    parts: list[str] = []
    for i in range(len(groups) - 1, -1, -1):
        g = groups[i]
        if g == 0:
            continue
        is_first = i == len(groups) - 1
        parts.append(_read3(g, full=not is_first) + units[i % 4] if i < 4 else _read3(g, not is_first))
    s = " ".join(parts).strip() + " đồng"
    return s[0].upper() + s[1:]


def due_date(start: date, days: int) -> date:
    return start + timedelta(days=days)


def parse_date(s: str) -> date | None:
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except (ValueError, AttributeError):
            pass
    return None
