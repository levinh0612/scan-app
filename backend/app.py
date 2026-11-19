"""API quét giấy tờ — chạy hoàn toàn offline, ảnh chỉ xử lý trong RAM, không ghi đĩa."""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import printers
from jobs import JobStore
from validators import (check_cccd, check_plate, fix_vin_like, normalize_plate,
                        parse_cccd_qr)

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Scan cầm đồ")

_ocr = None


def get_ocr():
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr = RapidOCR()
    return _ocr


# ---------------- Ảnh ----------------
def decode_image(data: bytes) -> np.ndarray | None:
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None
    h, w = img.shape[:2]
    s = 1800 / max(h, w)
    return cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC) if s != 1 else img


def enhance(img: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)


def read_qr(img: np.ndarray) -> str | None:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    try:                                    # zxing-cpp đọc QR dày/nghiêng tốt hơn OpenCV
        import zxingcpp
        for v in (img, gray, cv2.resize(gray, None, fx=1.5, fy=1.5), cv2.resize(gray, None, fx=0.6, fy=0.6)):
            for r in zxingcpp.read_barcodes(v):
                if r.text:
                    return r.text
    except Exception:
        pass
    det = cv2.QRCodeDetector()
    for variant in (img, gray, cv2.resize(gray, None, fx=0.5, fy=0.5), cv2.resize(gray, None, fx=1.5, fy=1.5),
                    cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41, 10)):
        try:
            text, _, _ = det.detectAndDecode(variant)
        except cv2.error:
            continue
        if text:
            return text
    return None


# ---------------- OCR ----------------
class Line:
    def __init__(self, text: str, score: float, box):
        self.text, self.score = text.strip(), float(score)
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        self.y, self.x = sum(ys) / 4, min(xs)


def run_ocr(img: np.ndarray, tag: str = "") -> list[Line]:
    res, _ = get_ocr()(enhance(img))
    lines = [Line(t, s, b) for b, t, s in (res or [])]
    lines = sorted(lines, key=lambda l: (round(l.y / 12), l.x))
    if os.environ.get("SCAN_DEBUG") == "1":   # chỉ bật khi cần dò lỗi; chứa dữ liệu cá nhân, xoá log sau khi dùng
        print(f"[OCR {tag}]", *[f"{l.score:.2f} | {l.text}" for l in lines], sep="\n", flush=True)
    return lines


def _mask(t: str) -> str:
    """Che dữ liệu cá nhân: chữ → A, số → 9; chỉ giữ hình dạng để dò lỗi OCR."""
    return re.sub(r"[^\W\d_]", "A", re.sub(r"\d", "9", t))


def _quality(img) -> str:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return f"{img.shape[1]}x{img.shape[0]} nét={cv2.Laplacian(g, cv2.CV_64F).var():.0f} sáng={g.mean():.0f}"


def trace(tag: str, img, lines, qr) -> None:
    """Log an toàn mỗi lần quét: không chứa giá trị thật (xem SCAN_DEBUG nếu cần chữ gốc)."""
    shapes = [f"{_mask(l.text)}~{l.score:.2f}" for l in (lines or []) if any(c.isdigit() for c in l.text)][:14]
    print(f"[TRACE {tag}] {_quality(img)} | dòng={len(lines or [])} | QR={('có len=%d dạng=%s' % (len(qr), _mask(qr)[:60])) if qr else 'KHÔNG'} | số-dạng: {shapes}", flush=True)


def fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


LABELS = re.compile(r"bien so|number plate|plate no|nhan hieu|brand|so may|engine|so khung|chassis|mau son|colou?r|"
                    r"loai xe|so loai|noi dang ky|chu xe|owner|dia chi|address|nam san xuat|ho va ten|full name|"
                    r"noi thuong tru|noi cu tru|residence|ngay sinh|date of birth|gioi tinh|sex|quoc tich|nationality|"
                    r"que quan|place of origin|co gia tri|date of expiry|date of issue|ngay cap|dung tich|so cho|"
                    r"hoat dong|pham vi|trong pham|dac diem nhan dang|personal identi|ngay,? ?thang,? ?nam|date,? ?month")


def is_label(text: str) -> bool:
    return bool(LABELS.search(fold(text)))


def cut_at_label(text: str) -> str:
    """Hai ô nằm cùng hàng (vd 'HONDA Số loại(Model code): VISION') hay bị OCR gộp một dòng: cắt giá trị tại nhãn kế tiếp."""
    folded, idx = [], []
    for i, ch in enumerate(text):
        for c in fold(ch):
            folded.append(c)
            idx.append(i)
    m = LABELS.search("".join(folded))
    return text[:idx[m.start()]].strip(" :-(") if m and m.start() > 0 else text


BRANDS = re.compile(r"\b(honda|yamaha|suzuki|sym|piaggio|vespa|kymco|vinfast|ducati|kawasaki|bmw|toyota|hyundai|kia|ford|mazda|"
                    r"mitsubishi|nissan|mercedes|isuzu|peugeot|lexus|chevrolet)\b")


def find_brand(lines: list[Line]):
    for ln in lines:
        m = BRANDS.search(fold(ln.text))
        if m:
            return m.group(1).upper(), ln.score
    return None, 0.0


def after_label(lines: list[Line], pattern: str, allow_next: bool = True):
    """Giá trị đứng sau nhãn (cùng dòng sau dấu ':' hoặc dòng kế tiếp, nếu dòng kế không phải nhãn khác)."""
    rx = re.compile(pattern)
    for i, ln in enumerate(lines):
        if rx.search(fold(ln.text)):
            m = re.split(r"[:：]", ln.text, maxsplit=1)
            v = cut_at_label(m[1]) if len(m) == 2 else ""
            if len(v.strip()) >= 2 and not is_label(v):
                return v.strip(), ln.score
            if allow_next and i + 1 < len(lines) and not is_label(lines[i + 1].text):
                return lines[i + 1].text, min(ln.score, lines[i + 1].score)
    return None, 0.0


def address_after(lines: list[Line]):
    """Địa chỉ thường dài 2 dòng: nối các dòng sau nhãn cho tới khi gặp nhãn khác (tối đa 3 dòng)."""
    rx = re.compile(r"noi thuong tru|noi cu tru|cu tru|thuong tru|residence|resid")
    for i, ln in enumerate(lines):
        if not rx.search(fold(ln.text)):
            continue
        parts, score = [], ln.score
        m = re.split(r"[:：]", ln.text, maxsplit=1)
        if len(m) == 2 and len(m[1].strip()) >= 3:
            parts.append(m[1].strip())
        for nxt in lines[i + 1:i + 4]:
            if is_label(nxt.text) or len(nxt.text) < 3:
                break
            parts.append(nxt.text)
            score = min(score, nxt.score)
        if parts:
            return ", ".join(parts), score
    return None, 0.0


PLATE_RX = re.compile(r"\b(\d{2})\s?-?\s?([A-ZĐ]{1,2}\d?)\s?-?\s?(\d{3}\s?\.?\s?\d{2}|\d{4,5})(?!\d)")   # (?!\d) thay \b: chữ (T) nhỏ sau biển hay bị đọc dính liền, vd '47AC-123.45T'


def find_plate(lines: list[Line]):
    """Tìm chuỗi đúng khuôn biển số trong mọi dòng (tránh lấy nhầm dòng 'Nơi đăng ký')."""
    for ln in lines:
        m = PLATE_RX.search(ln.text.upper())
        if m:
            return f"{m.group(1)}{m.group(2)}-{re.sub(r'\s', '', m.group(3))}", ln.score
    return None, 0.0


def clean_vin(t: str | None) -> str:
    """Bỏ chữ nhãn lọt vào giá trị (vd 'SỐ KHUNG', 'CHASSIS NO') rồi chuẩn hoá."""
    if not t:
        return ""
    t = re.sub(r"(?i)s[oố]\s*(khung|m[aá]y)|chassis|engine|\bno\b[:.]?", " ", t)
    return fix_vin_like(t) if t.strip() else ""


def fix_honda_ids(khung: str, may: str, loai: str):
    """Honda VN: số khung = RLH + mã loại (KF530…) …; số máy bắt đầu bằng 4 ký tự đầu mã loại (KF53…).
    Dùng số máy làm mốc: bỏ ký tự thừa chen sau 'RL', sửa 'RLB'→'RLH', và sửa số loại khi cả số máy lẫn số khung cùng 'bầu' cho một giá trị.
    Trả về (khung, loai, ghi_chú_khung, ghi_chú_loai)."""
    nk = nl = ""
    k, key = khung, (may or "")[:4]
    if k.startswith("RL") and len(key) == 4 and key.isalnum():
        if k[3:7] != key:
            for i in (3, 4):                                  # ký tự thừa ngay sau RLH
                c = k[:i] + k[i + 1:]
                if len(k) == 18 and c[3:7] == key:
                    k, nk = c, "Máy đã tự bỏ 1 ký tự thừa"
                    break
        if k[2] in "B8" and k[3:7] == key and len(k) in (17, 18):
            k, nk = k[:2] + "H" + k[3:], (nk + "; " if nk else "") + "Máy đã tự sửa chữ thứ 3 thành H"
    if loai and k[3:7] == key and loai[:4] != key and sum(a != b for a, b in zip(loai[:4], key)) == 1:
        nl = "Máy đã tự sửa 1 ký tự cho khớp số máy"
        loai = key + loai[4:]
    return k, loai, nk, nl


def valid_engine(v: str) -> bool:
    """Số máy thật: 7–16 ký tự chữ+số, có ≥4 chữ số. Loại chuỗi rác toàn chữ (lọt từ dòng nhãn khác)."""
    return bool(v) and 7 <= len(v) <= 16 and sum(c.isdigit() for c in v) >= 4 and bool(re.fullmatch(r"[A-Z0-9]+", v))


ENGINE_RX = re.compile(r"\b([A-Z]{1,3}\d{2}[A-Z]?\d{5,8}|[A-Z0-9]{9,14})\b")


def find_engine_like(lines):
    """Chuỗi giống số máy ở bất kỳ dòng nào (không phải số khung 17 ký tự, không phải biển số)."""
    best, bs = "", 0.0
    for ln in lines:
        for m in ENGINE_RX.finditer(ln.text.upper().replace(" ", "")):
            c = m.group(1)
            if len(c) != 17 and valid_engine(c) and not PLATE_RX.search(c) and sum(ch.isalpha() for ch in c) >= 2 and ln.score > bs:
                best, bs = c, ln.score
    return best, bs


def mrz_name(lines) -> str:
    """Dòng MRZ họ tên: NGUYEN<VAN<AN<<<<<  (OCR hay đọc '<' thành 'K')."""
    for ln in lines:
        t = ln.text.upper().replace(" ", "")
        if t.count("<") >= 3 and re.match(r"^[A-Z<K]+$", t) and not t.startswith("ID"):
            parts = [p for p in re.split(r"[<]+", t) if p]
            if not parts:
                continue
            parts = [re.sub(r"K+$", "", p) if len(p) > 2 else p for p in parts]
            parts = [p for p in parts if p and set(p) != {"K"}]
            if len(parts) >= 2:
                return " ".join(parts)
    return ""


def field(value, status="ok", note="", score=None):
    return {"value": value or "", "status": status if value else "missing", "note": note if value else "Không đọc được — vui lòng nhập", "conf": score}


def by_conf(value, score, thr=0.93, note_low="Máy không chắc chắn, hãy so với ảnh gốc"):
    if not value:
        return field("")
    return field(value, "ok" if score >= thr else "check", "" if score >= thr else note_low, round(score, 3))


# ---------------- Parse từng loại giấy ----------------
def parse_cccd(front: list[Line] | None, back: list[Line] | None, qr_text: str | None, out: dict, warnings: list):
    qr = parse_cccd_qr(qr_text) if qr_text else None
    if qr:
        out["cccd"] = field(qr["cccd"], "ok", "Từ mã QR (chính xác)")
        for k, qk in (("ho_ten", "ho_ten"), ("dia_chi", "dia_chi"), ("ngay_cap", "ngay_cap")):
            if qr.get(qk):
                out[k] = field(qr[qk], "ok", "Từ mã QR (chính xác)")
    elif qr_text:
        warnings.append("Quét được QR CCCD nhưng định dạng lạ, dùng OCR thay thế")

    lines = (front or []) + (back or [])
    if not lines:
        return
    if "cccd" not in out or not out["cccd"]["value"]:
        digits = None
        for ln in lines:
            m = re.search(r"\b(\d{3}\s?\d{3}\s?\d{3}\s?\d{3})\b|\b(\d{12})\b", ln.text.replace(" ", "") if len(ln.text) < 20 else ln.text)
            if m:
                digits = re.sub(r"\s", "", m.group(0))
                if len(digits) == 12:
                    out["cccd"] = by_conf(digits, ln.score, 0.95)
                    break
    if "cccd" not in out or not out["cccd"]["value"]:
        if any(re.search(r"chung minh|cmnd", fold(ln.text)) for ln in lines):         # CMND 9 số (loại cũ)
            for ln in lines:
                m = re.search(r"(?<!\d)(\d{9})(?!\d)", ln.text.replace(" ", ""))
                if m:
                    out["cccd"] = field(m.group(1), "check", "Đây là CMND 9 số (loại cũ), không phải CCCD 12 số — hãy yêu cầu khách đưa CCCD/thẻ căn cước", ln.score)
                    warnings.append("Giấy tờ là CMND 9 số (loại cũ) — cần CCCD/thẻ căn cước 12 số")
                    break
    if "ho_ten" not in out:
        mrz = mrz_name(back or [])
        if mrz:
            out["ho_ten"] = field(mrz, "check", "Lấy từ dòng mã máy đọc, không có dấu — hãy gõ lại dấu tiếng Việt")
    if "ho_ten" not in out:
        t, s = after_label(front or [], r"ho va ten|full name")
        out["ho_ten"] = field(t.upper() if t else "", "check", "OCR có thể mất dấu tiếng Việt — hãy soát kỹ", s) if t else field("")
    if "dia_chi" not in out:
        t, s = address_after(lines)
        out["dia_chi"] = by_conf(t, s, 0.97, "Địa chỉ dài, dễ sai — hãy soát") if t else field("")
    if "ngay_cap" not in out:
        DRX = r"(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4})"
        both = (back or []) + (front or [])
        for i, ln in enumerate(both):
            f = fold(ln.text).replace(" ", "")
            if ("namcap" in f or "dateofissue" in f or "ofissue" in f) and "het" not in f and "expiry" not in f:
                for cand in both[i:i + 3]:
                    m = re.search(DRX, cand.text)
                    if m:
                        out["ngay_cap"] = by_conf(f"{int(m[1]):02d}/{int(m[2]):02d}/{m[3]}", cand.score, 0.95)
                        break
                if "ngay_cap" in out:
                    break
    # Kiểm tra chéo số CCCD
    c = out.get("cccd", {}).get("value")
    if c:
        errs = check_cccd(c)
        if errs:
            out["cccd"]["status"], out["cccd"]["note"] = "check", "; ".join(errs)


def dot_plate(num: str) -> str:
    """Biển 5 số in dạng 988.06; biển 4 số giữ nguyên (1234)."""
    d = num.replace(".", "")
    return f"{d[:3]}.{d[3:]}" if len(d) == 5 else d


MAU_VI = {"den": "Đen", "trang": "Trắng", "do": "Đỏ", "xanh": "Xanh", "vang": "Vàng", "bac": "Bạc", "xam": "Xám", "nau": "Nâu",
          "hong": "Hồng", "cam": "Cam", "tim": "Tím", "ghi": "Ghi", "luc": "Lục", "lam": "Lam", "dong": "Đồng", "kem": "Kem",
          "dam": "đậm", "nhat": "nhạt", "la": "lá", "duong": "dương", "chuoi": "chuối", "ngoc": "ngọc", "tro": "tro"}


MAU_BODY = {"den", "trang", "do", "xanh", "vang", "bac", "xam", "nau", "hong", "cam", "tim", "ghi", "luc", "lam", "dong", "kem"}
MAU_MOD = {"dam", "nhat", "la", "duong", "chuoi", "ngoc", "tro"}      # đứng sau màu chính: 'Xanh lá', 'Xanh dương', 'Xám đậm'


_NHAM = {frozenset(p) for p in ("au", "ao", "ou", "ae", "ec", "il", "mn", "nh", "rn", "0o", "ui", "iu", "ty", "dd", "dc", "ng")}   # cặp ký tự OCR hay đọc nhầm
_NGUYEN_AM = set("aeiouy")


def _lev(a: str, b: str) -> float:
    """Khoảng cách chỉnh sửa có trọng số: thay ký tự hay bị đọc nhầm (a/u, m/n...) rẻ; mất nguyên âm rẻ hơn mất phụ âm."""
    prev = [0.0]
    for cb in b:
        prev.append(prev[-1] + (0.7 if cb in _NGUYEN_AM else 1.0))
    for ca in a:
        cur = [prev[0] + (0.7 if ca in _NGUYEN_AM else 1.0)]
        for j, cb in enumerate(b, 1):
            sub = 0.0 if ca == cb else (0.4 if frozenset((ca, cb)) in _NHAM else 1.0)
            cur.append(min(prev[j] + (0.7 if ca in _NGUYEN_AM else 1.0), cur[j - 1] + (0.7 if cb in _NGUYEN_AM else 1.0), prev[j - 1] + sub))
        prev = cur
    return prev[-1]


def _skel(w: str) -> str:
    return re.sub("[aeiouy]", "", w).replace("m", "n")


def _match_mau(k: str) -> str | None:
    """Khớp từ màu chịu sai/mất ký tự: 'xum', 'xun', 'xm' → 'xam'. Cùng chữ đầu; ngưỡng ≤1.0 (từ ≤4 ký tự) hoặc ≤2.0; phải nổi trội so với ứng viên thứ hai."""
    if k in MAU_VI:
        return k
    if len(k) < 2:
        return None
    lim = 1.0 if len(k) <= 4 else 2.0
    c = sorted((_lev(k, m), m) for m in MAU_VI if m[0] == k[0])
    if len(k) >= 3 and sum(m.startswith(k) for m in MAU_VI) >= 1:
        return None                                  # 'xan' có thể là 'xanh' đọc thiếu chữ → không tự đoán
    sk = _skel(k)                                    # cùng khung phụ âm (m≈n), nguyên âm đọc sai: 'xin','xun','xum' → 'xám'
    same = [m for m in MAU_VI if m[0] == k[0] and _skel(m) == sk]
    if len(same) == 1 and len(sk) >= 2:
        return same[0]
    c = [x for x in c if x[0] <= lim + 1e-9]
    return c[0][1] if c and (len(c) == 1 or c[0][0] + 0.2 <= c[1][0]) else None


def fix_mau(v: str) -> str:
    """OCR mất dấu / sai chữ: 'Do,Xum' hay 'đỏ xm' → 'Đỏ, Xám'; 'Xanh la' → 'Xanh lá'."""
    out: list[str] = []
    for w in re.split(r"[\s,;/]+", v.strip()):
        if not w:
            continue
        m = _match_mau(fold(w))
        word = MAU_VI[m] if m else w.capitalize()
        if m in MAU_MOD and out:
            out[-1] += " " + word
        else:
            out.append(word)
    return ", ".join(out)


def tidy_val(v: str) -> str:
    """Bỏ dấu/ký tự thừa ở đầu cuối giá trị (vd ') KF530 AIR' do nhãn '(Model code)' đọc dính)."""
    for _ in range(4):
        v = re.sub(r"^[\W_]+|[\W_]+$", "", re.sub(r"^[\W_]*\w?\)\s*", "", v))
    return v


def find_model(lines: list[Line]):
    """Số loại (model): 'Số loại(Model code): VISION' — thường nằm CÙNG hàng với nhãn hiệu nên không dùng after_label."""
    for i, ln in enumerate(lines):
        m = re.search(r"(?i)mo?d[eo]?l?\s*c[o0]d[eo]?\)?\s*[:;]?\s*(.*)$", ln.text) or re.search(r"(?i)^\s*s[oố0]\s*lo[aạ]i\s*[:;]?\s*(.*)$", ln.text)
        if not m:
            continue
        v = tidy_val(cut_at_label(m[1]))
        if len(v) >= 2 and not is_label(v):
            return v.upper(), ln.score
        if i + 1 < len(lines) and not is_label(lines[i + 1].text) and len(lines[i + 1].text.strip()) >= 2:
            return tidy_val(lines[i + 1].text).upper(), min(ln.score, lines[i + 1].score)
    return None, 0.0


def parse_cavet(lines: list[Line], qr_text: str | None, out: dict, warnings: list):
    plate_qr = None
    if qr_text:
        m = re.match(r"^([0-9]{2}[A-Z]{1,2}[0-9]?)[-]?([0-9.]{4,6})", qr_text.upper().replace(" ", ""))
        if m:
            plate_qr = f"{m.group(1)}-{dot_plate(m.group(2))}"
        else:
            warnings.append(f"QR cà vẹt đọc được '{qr_text[:30]}' nhưng không nhận dạng được biển số")
    plate_ocr, sc = find_plate(lines)
    plate_ocr = normalize_plate(plate_ocr) if plate_ocr else None
    if plate_ocr and "-" in plate_ocr and "." not in plate_ocr:
        h, t = plate_ocr.split("-", 1)
        plate_ocr = f"{h}-{dot_plate(t)}"
    if plate_qr and plate_ocr and re.sub(r"[-.]", "", plate_qr) != re.sub(r"[-.]", "", plate_ocr):
        out["bks"] = field(plate_qr, "check", f"QR: {plate_qr} ≠ OCR: {plate_ocr} — hãy xem tận mắt biển số", sc)
    elif plate_qr:
        if plate_ocr and "." in plate_ocr:                     # giữ đúng cách in trên cà vẹt
            plate_qr = plate_ocr
        out["bks"] = field(plate_qr, "ok", "QR trùng khớp OCR" if plate_ocr else "Từ mã QR (chính xác)")
    elif plate_ocr:
        out["bks"] = field(plate_ocr, "ok" if check_plate(plate_ocr) and sc >= .95 else "check",
                           "" if check_plate(plate_ocr) and sc >= .95 else "Biển số không đúng khuôn dạng / máy không chắc", sc)
    else:
        out["bks"] = field("")

    t, s = after_label(lines, r"nhan hieu|brand")
    if not t or not BRANDS.search(fold(t)):                      # nhãn đọc hỏng → tìm tên hãng ở mọi dòng
        tb, sb = find_brand(lines)
        t, s = (tb, sb) if tb else (t, s)
    out["nhan_hieu"] = by_conf(tidy_val(t) if t else t, s, 0.9)
    t, s = find_model(lines)
    out["so_loai"] = field(t, "check", "Số loại: soát từng ký tự với cà vẹt (dễ nhầm F/P, 0/O, 5/S)", round(s, 3)) if t else field("")
    t, s = after_label(lines, r"so may|engine")
    v = clean_vin(t)
    if not valid_engine(v):                                        # nhãn đọc hỏng → lấy nhầm dòng khác (vd dòng màu sơn) → tìm chuỗi giống số máy ở mọi dòng
        v2, s2 = find_engine_like(lines)
        v, s = (v2, s2) if v2 else ("", s)
    out["so_may"] = field(v, "check", "Số máy: soát từng ký tự (dễ nhầm O/0, I/1, B/8)", s) if v else field("")
    sl, sm = out["so_loai"].get("value", ""), v or ""
    if sl and sm and sl[:4] != sm[:4] and sum(a != b for a, b in zip(sl[:4], sm[:4])) == 1 and sl[:2].isalpha():
        out["so_loai"]["note"] = f"Số loại '{sl}' khác đầu số máy '{sm[:4]}' đúng 1 ký tự — có thể đọc sai, soát lại với cà vẹt"
    t, s = after_label(lines, r"so khung|chassis")
    v = clean_vin(t)
    note = "Số khung: soát từng ký tự (dễ nhầm O/0, I/1, B/8)" + (f". Đọc được {len(v)} ký tự, số khung chuẩn có 17 — có thể thừa/thiếu ký tự" if v and len(v) != 17 else "")
    out["so_khung"] = field(v, "check", note, s) if v else field("")
    if v and out["so_may"].get("value") and out["so_loai"].get("value") is not None:
        k2, l2, nk, nl = fix_honda_ids(v, out["so_may"]["value"], out["so_loai"].get("value", ""))
        if k2 != v:
            out["so_khung"] = field(k2, "check", f"{nk}. Chú nhìn lại cà vẹt cho chắc" + (f" (đang có {len(k2)} ký tự, chuẩn là 17)" if len(k2) != 17 else ""), s)
        if l2 != out["so_loai"].get("value", ""):
            out["so_loai"] = field(l2, "check", nl + ". Chú nhìn lại cà vẹt cho chắc", out["so_loai"].get("conf", 0))
    t, s = after_label(lines, r"mau son|color|colour")
    mv = fix_mau(t) if t else ""
    toks = [w for w in re.split(r"[\s,;/]+", t or "") if w]
    if mv and not (any(_match_mau(fold(w)) in MAU_BODY for w in toks) and all(_match_mau(fold(w)) for w in toks)):
        mv = ""                                       # MỌI từ phải là tên màu/từ bổ nghĩa; dòng rác ('Hlgt Dghg Trắng Phdm Vi' từ 'Hoạt động trong phạm vi') → bỏ, để người dùng chọn
    out["mau"] = field(mv, "check", "Màu sơn hay đọc sai: so với cà vẹt, bấm chọn lại màu bên dưới nếu cần", s) if mv else field("")


# ---------------- API ----------------
@app.post("/api/scan")
async def scan(cccd_front: UploadFile | None = File(None), cccd_back: UploadFile | None = File(None),
               cavet: UploadFile | None = File(None)):
    out: dict = {}
    warnings: list[str] = []

    async def load(f):
        return decode_image(await f.read()) if f else None

    imgs = {"front": await load(cccd_front), "back": await load(cccd_back), "cavet": await load(cavet)}
    for k, v in imgs.items():
        if v is None and {"front": cccd_front, "back": cccd_back, "cavet": cavet}[k] is not None:
            warnings.append(f"Không mở được ảnh {k}")

    qr_cccd = next((q for q in (read_qr(imgs["front"]) if imgs["front"] is not None else None,
                                read_qr(imgs["back"]) if imgs["back"] is not None else None) if q), None)
    qr_cavet = read_qr(imgs["cavet"]) if imgs["cavet"] is not None else None

    f_lines = run_ocr(imgs["front"], "front") if imgs["front"] is not None else None
    b_lines = run_ocr(imgs["back"], "back") if imgs["back"] is not None else None
    if imgs["front"] is not None or imgs["back"] is not None:
        parse_cccd(f_lines, b_lines, qr_cccd, out, warnings)
    if imgs["cavet"] is not None:
        c_lines = run_ocr(imgs["cavet"], "cavet")
        trace("cavet", imgs["cavet"], c_lines, qr_cavet)
        parse_cavet(c_lines, qr_cavet, out, warnings)
    for tag, im, ln in (("front", imgs["front"], f_lines), ("back", imgs["back"], b_lines)):
        if im is not None:
            trace(tag, im, ln, qr_cccd)
    print("[TRACE kết quả] " + " ".join(f"{k}={v.get('status')}" for k, v in out.items()) + (f" | cảnh báo={len(warnings)}" if warnings else ""), flush=True)
    return {"fields": out, "warnings": warnings}


@app.post("/api/peek")
async def peek(kind: str = Form(...), image: UploadFile = File(...)):
    """Xem trước trực tiếp trên màn hình camera: đọc nhanh 1 khung hình, KHÔNG lưu, KHÔNG ghi log nội dung."""
    img = decode_image(await image.read())
    if img is None or kind not in ("cavet", "cccd_front", "cccd_back"):
        raise HTTPException(400, "Ảnh không hợp lệ")
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sharp = float(cv2.Laplacian(g, cv2.CV_64F).var())
    qr = read_qr(img)
    lines = run_ocr(img, "peek")
    out: dict = {}
    if kind == "cavet":
        parse_cavet(lines, qr, out, [])
    elif kind == "cccd_front":
        parse_cccd(lines, None, qr, out, [])
    else:
        parse_cccd(None, lines, qr, out, [])
    return {"sharp": round(sharp), "qr": bool(qr),
            "fields": {k: {"value": v.get("value", ""), "status": v.get("status")} for k, v in out.items() if v.get("value")}}


def _lan_ip() -> str:
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as so:
            so.connect(("10.255.255.255", 1))               # không gửi gói nào, chỉ để hệ điều hành chọn card mạng đang dùng
            return so.getsockname()[0]
    except OSError:
        return ""


def _tunnel_url() -> str:
    root = Path(__file__).resolve().parent.parent
    try:
        pid = int((root / ".run" / "tunnel.pid").read_text().strip())
        os.kill(pid, 0)                                      # tunnel còn sống?
        m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", (root / "logs" / "tunnel.log").read_text(errors="ignore"))
        return m.group(0) if m else ""
    except Exception:
        return ""


def _qr_uri(url: str) -> str:
    try:
        import segno
        return segno.make(url, error="l", boost_error=False).svg_data_uri(scale=6, border=2)
    except Exception:
        return ""


@app.get("/api/links")
def links(request: Request):
    """Địa chỉ để mở app trên điện thoại + mã QR (SVG), tính ở máy chủ nên luôn đúng với lần chạy hiện tại."""
    port = request.url.port or int(os.environ.get("PORT", "8000"))
    items = []
    ip = _lan_ip()
    if ip:
        u = f"{request.url.scheme}://{ip}:{port}"
        sec = request.url.scheme == "https"
        items.append({"label": "Cùng wifi", "note": ("Lần đầu điện thoại báo 'không an toàn': bấm Nâng cao → Tiếp tục. Camera dùng được." if sec else "Điện thoại phải cùng wifi với máy tính (chưa có camera trực tiếp)"), "url": u, "qr": _qr_uri(u)})
    t = _tunnel_url()
    if t:
        items.append({"label": "Link https", "note": "Dùng được camera, mở từ mọi nơi", "url": t, "qr": _qr_uri(t)})
    return {"items": items}


@app.get("/api/printer")
def printer_status():
    return printers.cached()


@app.get("/api/health")
def health():
    return {"ok": True}


# ---------------- Hàng đợi lệnh in (RAM, dùng chung điện thoại + máy tính) ----------------
store = JobStore()


async def _body(request: Request) -> dict:
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(400, "Dữ liệu gửi lên không hợp lệ")
    if not isinstance(data, dict):
        raise HTTPException(400, "Dữ liệu gửi lên không hợp lệ")
    return data


@app.get("/api/jobs")
def list_jobs():
    return store.list()


@app.post("/api/jobs")
async def create_job(request: Request):
    d = await _body(request)
    try:
        return store.create(d.get("bks", ""), d.get("xe", ""), d.get("chu", ""), d.get("snapshot"),
                            d.get("status", "cho_in"))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/jobs/{jid}/snapshot")
def job_snapshot(jid: str):
    snap = store.snapshot(jid)
    if snap is None:
        raise HTTPException(404, "Không tìm thấy lệnh in (có thể đã hết hạn)")
    return snap


@app.patch("/api/jobs/{jid}")
async def update_job(jid: str, request: Request):
    d = await _body(request)
    try:
        job = store.update(jid, d.get("status", ""))
    except ValueError as e:
        raise HTTPException(400, str(e))
    if job is None:
        raise HTTPException(404, "Không tìm thấy lệnh in")
    return job


@app.delete("/api/jobs/{jid}")
def delete_job(jid: str):
    if not store.delete(jid):
        raise HTTPException(404, "Không tìm thấy lệnh in")
    return {"ok": True}


app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")


@app.get("/")
def index():
    return FileResponse(ROOT / "frontend" / "index.html", headers={"Cache-Control": "no-store"})
