"""Đọc ảnh giấy tờ: tiền xử lý ảnh, OCR, QR và bóc tách CCCD / cà vẹt."""
from __future__ import annotations
import cv2
import math
import numpy as np
import os
import re
import unicodedata

from validators import check_cccd, check_plate, fix_vin_like, normalize_plate, parse_cccd_qr


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


def _unsharp(img: np.ndarray) -> np.ndarray:
    return cv2.addWeighted(img, 1.6, cv2.GaussianBlur(img, (0, 0), 3), -0.6, 0)


def _upscale(img: np.ndarray) -> np.ndarray:
    return _unsharp(cv2.resize(enhance(img), None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC))


def flatten(img: np.ndarray) -> np.ndarray:
    """Làm phẳng nền: chia cho nền ước lượng → nền trắng đều (hết bóng đổ, ngả màu), chữ giữ sắc độ mềm.
    (Nhị phân hoá cứng đen/trắng đã đo: đọc TỆ hơn, vì hoa văn nền làm chữ đứt/dính.)"""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    bg = cv2.GaussianBlur(cv2.dilate(g, np.ones((15, 15), np.uint8)), (0, 0), 25)
    n = np.clip(g / np.maximum(bg, 1) * 255, 0, 255).astype(np.uint8)
    return cv2.cvtColor(n, cv2.COLOR_GRAY2BGR)


# Các lượt đọc cà vẹt: mỗi lượt xử lý ảnh khác nhau để lỗi ngẫu nhiên của lượt này bị lượt kia sửa
CAVET_RUNS = (("clahe", enhance, 1.0), ("raw", lambda im: im, 1.0), ("up", _upscale, 1.5), ("flat", flatten, 1.0))


def skew_angle(lines: list[Line]) -> float:
    """Góc nghiêng trung vị của các dòng chữ dài (độ). 0 nếu không đủ dữ liệu."""
    a = sorted(l.angle for l in lines if len(l.text) >= 8 and (l.box[2] - l.box[0]) > 2.5 * (l.box[3] - l.box[1]) / 1.0)
    return a[len(a) // 2] if len(a) >= 3 else 0.0


def rotate_img(img: np.ndarray, deg: float) -> np.ndarray:
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1.0)
    c, s = abs(M[0, 0]), abs(M[0, 1])
    nw, nh = int(h * s + w * c), int(h * c + w * s)
    M[0, 2] += nw / 2 - w / 2
    M[1, 2] += nh / 2 - h / 2
    return cv2.warpAffine(img, M, (nw, nh), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def deskew(img: np.ndarray, lines: list[Line]):
    """Xoay ảnh cho dòng chữ nằm ngang khi nghiêng ≥1° (và ≤25°). Trả (ảnh, dòng OCR tương ứng)."""
    ang = skew_angle(lines)
    if not (1.0 <= abs(ang) <= 25.0):
        return img, lines
    rot = rotate_img(img, ang)               # getRotationMatrix2D: góc dương = xoay ngược chiều kim đồng hồ → bù đúng chiều nghiêng xuống phải
    return rot, run_ocr(rot, "deskew")


KNOWN_MODELS = (
    "VISION", "WAVE", "ALPHA", "AIRBLADE", "BLADE", "LEAD", "WINNER", "FUTURE", "DREAM", "SONIC", "VARIO", "CLICK", "SUPERCUB", "MSX", "RSX",
    "EXCITER", "SIRIUS", "JUPITER", "VIXION", "JANUS", "GRANDE", "LATTE", "FREEGO", "NOZZA", "NVX", "MIO", "CYGNUS", "LUVIAS", "FAZZIO",
    "RAIDER", "SATRIA", "AXELO", "IMPULSE", "ADDRESS", "VIVA", "HAYATE", "SMASH", "ATTILA", "ELEGANT", "ANGELA", "GALAXY",
    "LIBERTY", "MEDLEY", "VESPA", "SPRINT", "PRIMAVERA", "KYMCO", "LIKE", "FINO", "VINFAST", "KLARA", "FELIZ", "EVO",
)


def _edit1(a: str, b: str) -> bool:
    """a, b khác nhau đúng 1 ký tự thay thế (cùng độ dài)."""
    return len(a) == len(b) and sum(x != y for x, y in zip(a, b)) == 1


def pick_known_model(res: dict, outs: list) -> None:
    """Số loại là chữ (VIXION, EXCITER…): nếu một lượt đọc ra đúng tên xe phổ biến thì chọn nó; nếu không lượt nào đúng mà giá trị
    chỉ lệch 1 ký tự so với đúng 1 tên xe → gợi ý tên đó. Luôn để trạng thái 'check' và ghi chú để người dùng soát."""
    f = res.get("so_loai") or {}
    v = norm_model(f.get("value", ""))
    if not v or v in KNOWN_MODELS or not v.isalpha():
        return
    seen = [norm_model((o.get("so_loai") or {}).get("value", "")) for o in outs]
    exact = [x for x in seen if x in KNOWN_MODELS]
    if exact:
        pick = max(set(exact), key=exact.count)
        why = "một lượt đọc khác ra đúng tên xe này"
    else:
        near = [m for m in KNOWN_MODELS if _edit1(v, m) and len(m) >= 4]
        if len(near) != 1:
            return
        pick, why = near[0], f"giống tên xe phổ biến, đọc '{f['value']}'"
    f["value"] = pick
    f["status"] = "check"
    f["note"] = f"Đã chọn '{pick}' ({why}). Soát lại với cà vẹt"


def norm_model(v: str) -> str:
    v = re.sub(r"^\s*[A-Za-z]?\s*[:;.,|]\s*", "", v or "")     # rác trước giá trị: 'L:VTXION' (dấu ':' của nhãn bị đọc thành chữ)
    return re.sub(r"[^A-Z0-9]", "", fold(v).upper())


def vote_log(tag: str, outs: list, res: dict) -> None:
    """Mỗi ô xe: giá trị từng lượt đọc → kết quả chốt. Mặc định che chữ (A/9); đặt SCAN_DEBUG=1 để thấy chữ thật khi dò lỗi."""
    raw = os.environ.get("SCAN_DEBUG") == "1"
    show = (lambda v: v) if raw else _mask
    names = [n for n, _, _ in CAVET_RUNS]
    for k in ("so_loai", "so_may", "so_khung", "mau", "nhan_hieu", "bks"):
        runs = " ".join(f"{n}={show((o.get(k) or {}).get('value') or '') or '-'}" for n, o in zip(names, outs))
        f = res.get(k) or {}
        print(f"[VOTE {tag}] {k}: {runs} => {show(f.get('value') or '') or '-'} ({f.get('agree', 0)}/{f.get('of', len(outs))}) {f.get('status')}", flush=True)


_MAU_STOP = {"dung", "tich", "dang", "plate", "color", "colour", "capacity", "capaci", "phu", "quoc", "thang", "bien", "so", "ky", "xe", "co", "gia", "tri", "den ngay"}


def mau_from_text(txt: str) -> str:
    """Dải chữ quanh 'Màu sơn' bị OCR cắt thành nhiều mảnh ('(Color)xanh Trangd' + 'Den.'): lấy các từ NGAY SAU nhãn 'Color',
    bỏ từ rác (Dung/tich...), từ nào khớp tên màu (sai ≤1 ký tự) thì nhận, gặp 'Đăng ký...' thì dừng."""
    m = re.search(r"(?i)colou?r\W*", txt)
    if not m:
        return ""
    out: list[str] = []
    for w in re.split(r"[\s,;/\-.:)(]+", _unglue_mau(txt[m.end():]))[:9]:
        f = fold(w)
        if f in ("dang", "ky"):
            break
        if len(f) < 3 or f in _MAU_STOP or f in NOT_MAU:
            continue
        if f in ("anh", "xan", "xnh"):
            f, w = "xanh", "xanh"
        r = _match_mau(f)
        if r and r in MAU_BODY | MAU_MOD and (len(f) >= 4 or r == f):
            out.append(MAU_VI[r])
    return " ".join(dict.fromkeys(out)) if out else ""


def rescue_mau(img: np.ndarray, all_lines: list, res: dict, tag: str) -> None:
    """Dòng 'Màu sơn' hay bị bộ dò chữ bỏ sót (nằm sát/đè chữ hãng xe). Cả các lượt đều không thấy → cắt dải ngay dưới dòng 'Nhãn hiệu',
    phóng to rồi đọc riêng; chỉ nhận kết quả khi qua đúng bộ lọc màu của parse_cavet (luôn 'cần soát')."""
    if (res.get("mau") or {}).get("value"):
        return
    ref = next((l for ls in all_lines for l in ls if re.search(r"nhan hi|brand", fold(l.text))), None)
    if not ref:
        return
    h = max(ref.box[3] - ref.box[1], 1)
    H, W = img.shape[:2]
    y0, y1 = int(max(ref.box[1] + 0.6 * h, 0)), int(min(ref.box[3] + 2.6 * h, H))
    x0, x1 = int(max(ref.box[0] - 0.3 * h, 0)), int(min(ref.box[0] + 0.65 * W, W))
    if y1 - y0 < 20 or x1 - x0 < 60:
        return
    crop = img[y0:y1, x0:x1]
    best, bs = "", 0.0
    for name, pre, sc in (("m-up", _upscale, 1.5), ("m-clahe", enhance, 1.0), ("m-raw", lambda im: im, 1.0)):
        ls = run_ocr(crop, f"{tag}:{name}", pre, sc)
        v = mau_from_text(" ".join(l.text for l in ls))
        if len(v.split()) > len(best.split()):        # lượt nào đọc được nhiều màu hơn thì đúng hơn (chữ rớt thường làm MẤT màu chứ ít khi thêm)
            best, bs = v, max((l.score for l in ls), default=0.0)
    if best:
        res["mau"] = {**field(best, "check", "Màu đọc từ lượt dò riêng vùng 'Màu sơn' — hãy so với cà vẹt", bs), "agree": 1, "of": 1}


def read_cavet_multi(img: np.ndarray, qr: str | None, warnings: list, tag: str = "cavet"):
    """Đọc cà vẹt nhiều lượt + bỏ phiếu từng ô + cắt ảnh đối chiếu. Trả (kết quả, dòng OCR lượt đầu)."""
    import multiread
    img, first = deskew(img, run_ocr(img, f"{tag}:probe"))
    outs, all_lines = [], []
    for name, pre, sc in CAVET_RUNS:
        lines = first if name == "clahe" else run_ocr(img, f"{tag}:{name}", pre, sc)    # lượt CLAHE đã chạy khi dò góc nghiêng → dùng lại
        o: dict = {}
        parse_cavet(lines, qr, o, warnings if not outs else [])
        outs.append(o)
        all_lines.append(lines)
    res = multiread.vote(outs)
    b = res.get("bks") or {}
    if b.get("value") and b.get("status") == "check" and b.get("agree") == b.get("of") and check_plate(b["value"]):
        b["status"] = "ok"            # đúng khuôn dạng + mọi lượt đọc trùng nhau → bỏ cảnh báo 'máy không chắc'
        b["note"] = f"{b['of']}/{b['of']} lượt đọc trùng, đúng khuôn dạng"
    nh = res.get("nhan_hieu") or {}
    if nh.get("value") and nh.get("status") == "check" and nh.get("agree") == nh.get("of") and BRANDS.search(fold(nh["value"])):
        nh["status"], nh["note"] = "ok", f"{nh['of']}/{nh['of']} lượt đọc trùng, đúng tên hãng"
    rescue_mau(img, all_lines, res, tag)
    pick_known_model(res, outs)
    vote_log(tag, outs, res)
    multiread.attach_crops(res, all_lines, img)
    return res, all_lines[0]


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
    def __init__(self, text: str, score: float, box, scale: float = 1.0):
        self.text, self.score = text.strip(), float(score)
        ys = [p[1] / scale for p in box]          # scale: ảnh đưa vào OCR đã phóng to bao nhiêu lần so với ảnh gốc
        xs = [p[0] / scale for p in box]
        self.y, self.x = sum(ys) / 4, min(xs)
        self.box = (min(xs), min(ys), max(xs), max(ys))
        (x0, y0), (x1, y1) = box[0], box[1]        # cạnh trên của khung chữ → góc nghiêng của dòng (độ, dương = nghiêng xuống phải)
        self.angle = math.degrees(math.atan2(y1 - y0, x1 - x0)) if x1 > x0 else 0.0


def run_ocr(img: np.ndarray, tag: str = "", pre=None, scale: float = 1.0) -> list[Line]:
    res, _ = get_ocr()((pre or enhance)(img))
    lines = [Line(t, s, b, scale) for b, t, s in (res or [])]
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


BRANDS_LONG = re.compile(r"(honda|yamaha|suzuki|piaggio|vespa|kymco|vinfast|ducati|kawasaki|toyota|hyundai|mazda|mitsubishi|nissan|mercedes|isuzu|peugeot|lexus|chevrolet)")


def find_brand(lines: list[Line]):
    for ln in lines:
        m = BRANDS.search(fold(ln.text))
        if m:
            return m.group(1).upper(), ln.score
    for ln in lines:                                         # nhãn dính liền chữ ('BrumdYAMAHA'): bỏ ràng buộc ranh giới từ cho tên hãng dài
        m = BRANDS_LONG.search(fold(ln.text))
        if m:
            return m.group(1).upper(), ln.score
    return None, 0.0


def value_near(lab: "Line", lines: list["Line"]):
    """Giá trị của nhãn khi OCR tách thành 2 dòng: (1) cùng hàng, bên phải nhãn; (2) ngay dưới nhãn, chồng lên cột của nhãn
    (cà vẹt cũ: số máy/số khung căn lề phải, nằm HÀNG DƯỚI nhãn; dòng kế tiếp theo thứ tự đọc có thể là địa chỉ ở cột trái)."""
    h = max(lab.box[3] - lab.box[1], 1)
    cy = (lab.box[1] + lab.box[3]) / 2
    w = lab.box[2] - lab.box[0]
    best, bk = None, None
    for o in lines:
        if o is lab or not getattr(o, "box", None) or is_label(o.text) or len(o.text.strip()) < 3:
            continue
        dy = (o.box[1] + o.box[3]) / 2 - cy
        if abs(dy) < 0.7 * h and o.box[0] >= lab.box[0] + 0.6 * w:
            k = (0, o.box[0])
        elif 0.3 * h < dy < 2.4 * h and o.box[2] > lab.box[0] + 0.3 * w and o.box[0] < lab.box[2] + 0.3 * w:
            k = (1, dy)
        else:
            continue
        if bk is None or k < bk:
            best, bk = o, k
    return best


def glued_value(text: str, rx) -> str:
    folded, idx = [], []
    for i, ch in enumerate(text):
        for c in fold(ch):
            folded.append(c)
            idx.append(i)
    m = rx.search("".join(folded))
    if not m or m.end() >= len(idx):
        return ""
    rest = text[idx[m.end()]:]
    v = cut_at_label(re.sub(r"^[\s\)\(:;.]*(?:[a-z](?=[A-Z]))?", "", rest)).strip()
    return v if len(re.sub(r"[^A-Za-z0-9]", "", v)) >= 3 else ""             # 'N:' (nốt của 'Chassis N°:') không phải giá trị


def after_label(lines: list[Line], pattern: str, allow_next: bool = True):
    """Giá trị đứng sau nhãn (cùng dòng sau dấu ':' hoặc dòng kế tiếp, nếu dòng kế không phải nhãn khác)."""
    rx = re.compile(pattern)
    for i, ln in enumerate(lines):
        if rx.search(fold(ln.text)):
            m = re.split(r"[:：]", ln.text, maxsplit=1)
            v = cut_at_label(m[1]) if len(m) == 2 else ""
            if len(v.strip()) < 2:                          # OCR làm mất dấu ':' → giá trị dính liền sau nhãn: 'Mau sn (ColoriXam Den'
                v = glued_value(ln.text, rx)
            if len(v.strip()) >= 2 and not is_label(v):
                return v.strip(), ln.score
            r = value_near(ln, lines)
            if r:
                return r.text, min(ln.score, r.score)
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
    parts = t.split()
    if len(parts) > 1 and re.fullmatch(r"[A-Za-z0-9\-]{6,}", parts[-1]) and sum(c.isdigit() for c in parts[-1]) >= 3 \
            and any(re.fullmatch(r"[^\W\d_]{3,}", w) for w in parts[:-1]):
        t = parts[-1]                                   # dòng địa chỉ dính số khung ('… Huỳnh Văn Bánh P13PN 125T-1030472') → chỉ lấy token cuối
    v = fix_vin_like(t) if t.strip() else ""
    return v if sum(c.isdigit() for c in v) >= 3 else ""    # số khung/máy luôn có chữ số; 'CHASSSN' là chữ nhãn đọc hỏng


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
        if len(k) in (17, 18) and k[3:7] != key and sum(x != y for x, y in zip(k[3:7], key)) == 1:
            k, nk = k[:3] + key + k[7:], (nk + "; " if nk else "") + "Máy đã tự sửa 1 ký tự (vd J↔U) cho khớp số máy"
        if k[2] in "B8" and k[3:7] == key and len(k) in (17, 18):
            k, nk = k[:2] + "H" + k[3:], (nk + "; " if nk else "") + "Máy đã tự sửa chữ thứ 3 thành H"
    if loai and k[3:7] == key and loai[:4] != key and sum(a != b for a, b in zip(loai[:4], key)) == 1:
        nl = "Máy đã tự sửa 1 ký tự cho khớp số máy"
        loai = key + loai[4:]
    return k, loai, nk, nl


def valid_engine(v: str) -> bool:
    """Số máy thật: 7–16 ký tự chữ+số (ô tô có thể có dấu '-', vd L15Z1-1234567), có ≥4 chữ số. Loại chuỗi rác toàn chữ (lọt từ dòng nhãn khác)."""
    return bool(v) and 7 <= len(v) <= 16 and sum(c.isdigit() for c in v) >= 4 and bool(re.fullmatch(r"[A-Z0-9\-]+", v)) and not re.search(r"[A-Z]{6,}", v)


ENGINE_RX = re.compile(r"\b([A-Z]{1,3}\d{2}[A-Z]?\d{5,8}|[A-Z0-9]{9,14})\b")


def engine_above(lines: list[Line], khung: str) -> tuple[str, float]:
    """Cà vẹt cũ: số máy và số khung xếp chồng ở cột phải. Nhãn số máy hay bị OCR làm hỏng → lấy chuỗi giống số máy nằm NGAY TRÊN số khung."""
    kl = next((l for l in lines if getattr(l, "box", None) and clean_vin(l.text) == khung), None)
    if not kl:
        return "", 0.0
    best, by = None, -1.0
    for o in lines:
        if o is kl or not getattr(o, "box", None):
            continue
        c = clean_vin(o.text)
        if (c != khung and valid_engine(c) and not PLATE_RX.search(c) and o.box[3] <= kl.box[1] + 0.3 * (kl.box[3] - kl.box[1])
                and o.box[2] > kl.box[0] and o.box[0] < kl.box[2] and o.box[3] > by):
            best, by = o, o.box[3]
    return (clean_vin(best.text), best.score) if best else ("", 0.0)


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


_FIRST_CONF = {"y": "x", "v": "x"}      # chữ đầu hay bị đọc nhầm: 'Yam' → Xám


def _match_mau(k: str) -> str | None:
    if k in ("d", "dd"):                    # cà vẹt in 'Đỏ' ngắn: OCR chỉ còn chữ 'D'
        return "do"
    if re.fullmatch(r"[a-z]?[cdo]c?n", k) and k not in ("on",):   # 'Dcn'/'fcn'/'cn' → Đen
        return "den"
    r = _match_mau_core(k)
    if r or k[:1] not in _FIRST_CONF:
        return r
    return _match_mau_core(_FIRST_CONF[k[0]] + k[1:])


def _match_mau_core(k: str) -> str | None:
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


NOT_MAU = {"nam", "hai", "banh", "cm", "xe", "dung", "tich", "so", "may", "khung", "loai", "phong", "truong", "ngay", "thang", "chu"}


def find_color(lines: list[Line], ok) -> tuple[str, float]:
    """Giá trị màu khi nhãn 'Màu sơn' có mà giá trị nằm dòng khác: lấy dòng chỉ gồm tên màu NẰM QUANH nhãn (cùng hàng bên phải, hoặc ngay dưới);
    giá trị cũng có thể dính vào cuối dòng 'Số người được phép chở' ngay dưới nhãn (cà vẹt cũ)."""
    lab = next((l for l in lines if getattr(l, "box", None) and re.search(r"colou?r|mau s", fold(l.text))), None)
    if not lab:
        return "", 0.0
    tail = re.sub(r"(?is)^.*?colou?r[\W_]*", "", lab.text).strip(" .:;,-") if "color" in fold(lab.text) else ""
    if 3 <= len(tail) <= 24 and ok(tail):                  # giá trị dính liền sau nhãn: 'Màu sơn(Color).Trắng Đen'
        return tail, lab.score
    h = max(lab.box[3] - lab.box[1], 1)
    cy = (lab.box[1] + lab.box[3]) / 2
    best, bk = None, None
    for o in lines:
        if o is lab or not getattr(o, "box", None):
            continue
        dy = (o.box[1] + o.box[3]) / 2 - cy
        if not (-0.6 * h <= dy <= 3.2 * h):
            continue
        txt = o.text
        if re.search(r"phep\s*ch[o0]", fold(txt)):
            txt = glued_value(txt, re.compile(r"phep ch[o0]")) or ""
        elif re.search(r"colou?r|mau s", fold(txt)) or is_label(txt):
            continue
        txt = txt.strip(" .:;,-")
        if 3 <= len(txt) <= 24 and ok(txt):
            k = (abs(dy), o.box[0])
            if bk is None or k < bk:
                best, bk = o, k
                got = txt
    return (got, best.score) if best else ("", 0.0)


def _unglue_mau(v: str) -> str:
    """'Xanh TrangDen' (OCR dính 2 màu liền, chỉ còn chữ hoa phân cách) → 'Xanh Trang Den'."""
    return re.sub(r"([a-zà-ỹ])([A-ZĐ])", r"\1 \2", v or "")


def fix_mau(v: str) -> str:
    """OCR mất dấu / sai chữ: 'Do,Xum' hay 'đỏ xm' → 'Đỏ Xám' (cách nhau bằng dấu cách, như trên thẻ); 'Xanh la' → 'Xanh lá'."""
    out: list[str] = []
    parts = [w for w in re.split(r"[\s,;/\-]+", _unglue_mau(v).strip()) if w]
    for w in parts:
        if not w:
            continue
        m = _match_mau(fold(w))
        if not m and len(w) <= 3 and out and w is parts[-1]:
            continue                                  # mảnh chữ hỏng ở cuối ('fcn'): bỏ, người dùng chọn màu còn thiếu
        word = MAU_VI[m] if m else w.capitalize()
        if m in MAU_MOD and out:
            out[-1] += " " + word
        else:
            out.append(word)
    return " ".join(out)


def tidy_val(v: str) -> str:
    """Bỏ dấu/ký tự thừa ở đầu cuối giá trị (vd ') KF530 AIR' do nhãn '(Model code)' đọc dính)."""
    for _ in range(4):
        v = re.sub(r"^[\W_]+|[\W_]+$", "", re.sub(r"^[\W_]*\w?\)\s*", "", v))
    return v


_NOT_MODEL = re.compile(r"(?i)ngay|date|expir|gia\s*tri|bien\s*so|plate|hoat|pham|truong|thanh|color|mau\s*s|khung|chassis|engine|may\b|ten chu|dia chi")


def plausible_model(txt: str) -> bool:
    """Dòng có thể là số loại: ngắn (≤ 2 từ, ≤ 16 ký tự), chỉ chữ/số, không phải nhãn/dòng khác của cà vẹt (tránh nhặt nhầm dòng mờ kế bên)."""
    t = tidy_val(txt)
    return bool(re.fullmatch(r"[A-Za-z0-9\-]{2,10}( [A-Za-z0-9\-]{1,6})?", t)) and not is_label(txt) and not _NOT_MODEL.search(fold(t))


_MODEL_SHAPE = re.compile(r"\b[A-Z]{1,3}\d{2,4}[A-Z0-9]?(?: ?[A-Z]{2,6})?\b")


def clean_model(v: str) -> str:
    """Nhãn '(Model code):' khi mờ bị đọc hỏng và dính vào giá trị ('MODEL EODE)KPSAO AIR'): lấy phần sau dấu ) hoặc : cuối cùng;
    nếu vẫn không giống số loại (dài / nhiều từ) thì tìm dạng 'KF530 AIR'; không có thì bỏ trống để người dùng nhập tay."""
    parts = [x.strip() for x in re.split(r"[)）:;]", v or "") if x.strip()]
    v = parts[-1] if parts else ""
    if plausible_model(v) or not v:
        return v
    m = _MODEL_SHAPE.search(v.upper())
    return m[0] if m else ""


def find_model(lines: list[Line]):
    """Số loại (model): 'Số loại(Model code): VISION' — thường nằm CÙNG hàng với nhãn hiệu nên không dùng after_label."""
    for i, ln in enumerate(lines):
        m = re.search(r"(?i)m[a-z]{1,5}\s*c[o0]d[eo]?[\)）]?\s*[:;]?\s*(?-i:(?:[a-z](?=[A-Z]))?)(.*)$", ln.text) or re.search(r"(?i)^\W*s[oố0ô6]\s*lo[aạ]?i?\s*[:;]?\s*(.*)$", ln.text)
        if not m:
            continue
        v = clean_model(tidy_val(cut_at_label(m[1])))
        if len(v) >= 2 and not is_label(v):
            return v.upper(), ln.score
        r = value_near(ln, lines)                      # giá trị ở dòng riêng, hơi lệch hàng so với nhãn (cà vẹt cũ: 'WAVE' nằm cao hơn nhãn)
        if r and not re.search(r"(?i)dung\s*t|capac|mode|code|\d{3,}", r.text) and re.fullmatch(r"[A-Za-z0-9 \-]{3,18}", tidy_val(r.text)):
            return tidy_val(r.text).upper(), min(ln.score, r.score)
        if i + 1 < len(lines) and plausible_model(lines[i + 1].text):
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
    t, s = after_label(lines, r"s[os6]\s?may|engine|eng n")
    v = clean_vin(t)
    if not valid_engine(v):                                        # nhãn đọc hỏng → lấy nhầm dòng khác (vd dòng màu sơn) → tìm chuỗi giống số máy ở mọi dòng
        v2, s2 = find_engine_like(lines)
        v, s = (v2, s2) if v2 else ("", s)
    out["so_may"] = field(v, "check", "Số máy: soát từng ký tự (dễ nhầm O/0, I/1, B/8)", s) if v else field("")
    _kh, _ks = after_label(lines, r"so khung|chassis")
    _kh = clean_vin(_kh)
    if _kh and (not v or v == _kh):                        # số máy trùng số khung = lấy nhầm: tìm chuỗi nằm ngay trên số khung
        _e, _es = engine_above(lines, _kh)
        if _e:
            v = _e
            out["so_may"] = field(v, "check", "Số máy: soát từng ký tự (dễ nhầm O/0, I/1, B/8)", _es)
    sl, sm = out["so_loai"].get("value", ""), v or ""
    if sl and sm and sl[:4] != sm[:4] and sum(a != b for a, b in zip(sl[:4], sm[:4])) == 1 and sl[:2].isalpha():
        out["so_loai"]["note"] = f"Số loại '{sl}' khác đầu số máy '{sm[:4]}' đúng 1 ký tự — có thể đọc sai, soát lại với cà vẹt"
    t, s = after_label(lines, r"so khung|chassis")
    v = clean_vin(t)
    note = "Số khung: soát từng ký tự (dễ nhầm O/0, I/1, B/8)" + (f". Đọc được {len(v)} ký tự, số khung chuẩn có 17 — có thể thừa/thiếu ký tự" if v and len(v) != 17 else "")
    out["so_khung"] = field(v, "check", note, s) if v else field("")
    if not v and out["so_may"].get("value"):                 # cà vẹt rất cũ: số máy và số khung cùng 1 hàng, nhãn số khung mất
        el = next((l for l in lines if getattr(l, "box", None) and clean_vin(l.text) == out["so_may"]["value"]), None)
        if el:
            hh = max(el.box[3] - el.box[1], 1)
            side = [o for o in lines if o is not el and getattr(o, "box", None) and abs((o.box[1] + o.box[3] - el.box[1] - el.box[3]) / 2) < 0.7 * hh
                    and o.box[0] > el.box[2] and re.fullmatch(r"[A-Za-z0-9.\-]{4,}", o.text.strip()) and sum(c.isdigit() for c in o.text) >= 3]
            if side:
                v, s = clean_vin(side[0].text.replace(".", "")), side[0].score
                out["so_khung"] = field(v, "check", "Số khung đọc theo vị trí (nhãn bị mờ) — soát với cà vẹt", s) if v else field("")
    if v and out["so_may"].get("value") and out["so_loai"].get("value") is not None:
        k2, l2, nk, nl = fix_honda_ids(v, out["so_may"]["value"], out["so_loai"].get("value", ""))
        if k2 != v:
            out["so_khung"] = field(k2, "check", f"{nk}. Chú nhìn lại cà vẹt cho chắc" + (f" (đang có {len(k2)} ký tự, chuẩn là 17)" if len(k2) != 17 else ""), s)
        if l2 != out["so_loai"].get("value", ""):
            out["so_loai"] = field(l2, "check", nl + ". Chú nhìn lại cà vẹt cho chắc", out["so_loai"].get("conf", 0))
    t, s = after_label(lines, r"mau son|color|colour")
    def _mau_ok(txt):
        tk = [w for w in re.split(r"[\s,;/\-]+", _unglue_mau(txt)) if w]
        if any(fold(w) in NOT_MAU for w in tk) or any(len(w) < 3 and fold(w) not in MAU_VI for w in tk):
            return False                              # 'Nam' (loại xe), 'cm' (dung tích) bị đọc nhầm thành màu Nâu/Cam
        miss = [w for w in tk if not _match_mau(fold(w))]
        return bool(tk) and any(_match_mau(fold(w)) in MAU_BODY for w in tk) and all(len(w) <= 3 for w in miss) and len(miss) <= 1   # tối đa 1 từ cụt ≤3 ký tự ('Trang fcn' → Trắng; 'Đen' đọc hỏng) bị bỏ
    mv = fix_mau(t) if t else ""
    if mv and not _mau_ok(t):
        mv = ""                                       # MỌI từ phải là tên màu/từ bổ nghĩa; dòng rác ('Hlgt Dghg Trắng Phdm Vi' từ 'Hoạt động trong phạm vi') → bỏ, để người dùng chọn
    if not mv:                                        # nhãn đọc hỏng / giá trị tách dòng → dò quanh dòng nhãn 'Màu sơn'
        cand, sc = find_color(lines, _mau_ok)
        if cand:
            mv, s = fix_mau(cand), sc
    out["mau"] = field(mv, "check", "Màu sơn hay đọc sai: so với cà vẹt, bấm chọn lại màu bên dưới nếu cần", s) if mv else field("")
