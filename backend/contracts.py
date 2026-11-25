"""Kho hợp đồng cầm đồ (SQLite, không cần cài thêm): lưu, cảnh báo trùng, gia hạn, chuộc, thống kê.

Ý tưởng chính
- Mọi số khung/số máy/biển số được CHUẨN HOÁ (bỏ dấu cách/gạch/chấm, in hoa) → khoá so khớp ổn định dù OCR/nhập tay khác kiểu gõ.
- Cảnh báo trùng KHÔNG chặn cứng (luật hay đổi, OCR hay sai 1 ký tự): trả danh sách cảnh báo có mức độ để giao diện hiển thị.
- Trạng thái 'quá hạn' không lưu cố định mà tính theo ngày hôm nay → không cần tác vụ nền.
- Mọi thay đổi (gia hạn/chuộc/thanh lý) ghi thành 'sự kiện' để truy vết.
"""
from __future__ import annotations

import csv
import io
import os
import re
import json
import shutil
import sqlite3
import threading
import unicodedata
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("SCAN_DB") or ROOT / "data" / "contracts.db")
_lock = threading.Lock()
NEAR_MIN_LEN = 8          # số khung/số máy từ 8 ký tự trở lên mới so "gần giống" (sai 1 ký tự)
SOON_DAYS = 3             # 'sắp đến hạn' = còn ≤ 3 ngày

SCHEMA = """
CREATE TABLE IF NOT EXISTS contracts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ma TEXT UNIQUE,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'dang_cam',
  ho_ten TEXT, cccd TEXT, ngay_cap TEXT, dia_chi TEXT, sdt TEXT,
  bks TEXT, nhan_hieu TEXT, so_loai TEXT, so_khung TEXT, so_may TEXT, mau TEXT,
  so_tien INTEGER DEFAULT 0, le_phi INTEGER DEFAULT 0, so_ngay INTEGER DEFAULT 0,
  tu_ngay TEXT, den_ngay TEXT,
  bks_k TEXT, khung_k TEXT, may_k TEXT, cccd_k TEXT, ten_k TEXT, dedupe TEXT,
  closed_at TEXT, closed_amount INTEGER, note TEXT DEFAULT '',
  nguon TEXT NOT NULL DEFAULT 'may_tinh'      -- nơi tạo hồ sơ: may_tinh | dien_thoai
);
CREATE INDEX IF NOT EXISTS ix_c_bks ON contracts(bks_k);
CREATE INDEX IF NOT EXISTS ix_c_khung ON contracts(khung_k);
CREATE INDEX IF NOT EXISTS ix_c_may ON contracts(may_k);
CREATE INDEX IF NOT EXISTS ix_c_cccd ON contracts(cccd_k);
CREATE INDEX IF NOT EXISTS ix_c_status ON contracts(status, den_ngay);
CREATE UNIQUE INDEX IF NOT EXISTS ux_c_dedupe ON contracts(dedupe);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contract_id INTEGER NOT NULL REFERENCES contracts(id),
  at TEXT NOT NULL, type TEXT NOT NULL,
  days INTEGER, amount INTEGER, den_ngay TEXT, note TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_e_c ON events(contract_id);
"""

TEXT_FIELDS = ("ho_ten", "cccd", "ngay_cap", "dia_chi", "sdt", "bks", "nhan_hieu", "so_loai", "so_khung", "so_may", "mau")
STATUSES = ("dang_cam", "da_chuoc", "thanh_ly", "huy")


# ---------- tiện ích chuẩn hoá ----------
def key(v) -> str:
    """Khoá so khớp: bỏ dấu tiếng Việt, chỉ giữ chữ+số, in hoa. 'G3J6 B-0189.542' → 'G3J6B0189542'."""
    s = unicodedata.normalize("NFD", str(v or "")).replace("đ", "d").replace("Đ", "D")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Za-z0-9]", "", s).upper()


def money(v) -> int:
    d = re.sub(r"\D", "", str(v or ""))
    return int(d) if d else 0


def parse_vn(s: str) -> date | None:
    m = re.fullmatch(r"\s*(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\s*", str(s or ""))
    if not m:
        return None
    try:
        return date(int(m[3]), int(m[2]), int(m[1]))
    except ValueError:
        return None


def to_vn(d: date | str | None) -> str:
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d)
        except ValueError:
            return ""
    return d.strftime("%d/%m/%Y") if d else ""


def near(a: str, b: str) -> bool:
    """Khác nhau đúng 1 ký tự (thay/thêm/bớt) — lỗi OCR kinh điển (B↔E, 8↔K, F↔P)."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    s, l = (a, b) if len(a) < len(b) else (b, a)
    i = 0
    while i < len(s) and s[i] == l[i]:
        i += 1
    return s[i:] == l[i + 1:]


# ---------- kết nối ----------
@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        con = sqlite3.connect(DB_PATH, timeout=10)
        con.row_factory = sqlite3.Row
        try:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA foreign_keys=ON")
            con.executescript(SCHEMA)
            cols = {r[1] for r in con.execute("PRAGMA table_info(contracts)")}
            if "ten_k" not in cols:
                con.execute("ALTER TABLE contracts ADD COLUMN ten_k TEXT")
            if "nguon" not in cols:
                con.execute("ALTER TABLE contracts ADD COLUMN nguon TEXT NOT NULL DEFAULT 'may_tinh'")
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()


def _view(r: sqlite3.Row, today: date | None = None) -> dict:
    """Hàng DB → dict cho giao diện, kèm trạng thái hiển thị (quá hạn/sắp hạn tính theo hôm nay)."""
    today = today or date.today()
    d = {k: r[k] for k in r.keys() if k not in ("bks_k", "khung_k", "may_k", "cccd_k", "ten_k", "dedupe")}
    d["den_ngay_vn"], d["tu_ngay_vn"] = to_vn(d.get("den_ngay")), to_vn(d.get("tu_ngay"))
    d["created_vn"] = (d.get("created_at") or "")[:16].replace("T", " ")
    disp, left = d["status"], None
    if d["status"] == "dang_cam" and d.get("den_ngay"):
        left = (date.fromisoformat(d["den_ngay"]) - today).days
        disp = "qua_han" if left < 0 else ("sap_han" if left <= SOON_DAYS else "dang_cam")
    d["hien_thi"], d["con_ngay"] = disp, left
    return d


def _brief(d: dict, local: bool) -> dict:
    """Thông tin hợp đồng trả cho cảnh báo. Gọi từ xa (qua tunnel) thì ẩn tên/CCCD."""
    b = {k: d[k] for k in ("id", "ma", "hien_thi", "den_ngay_vn", "tu_ngay_vn", "so_tien", "nhan_hieu", "bks", "con_ngay")}
    if local:
        b.update(ho_ten=d["ho_ten"], cccd=d["cccd"], sdt=d["sdt"])
    return b


# ---------- cảnh báo trùng ----------
def find_duplicates(con, f: dict, exclude_id: int | None = None, local: bool = True) -> list[dict]:
    """Trả danh sách cảnh báo: {level: high|warn|info, kind, field, msg, contract}. high = xe đang nằm ở tiệm (chưa chuộc)."""
    bk, kk, mk, ck = key(f.get("bks")), key(f.get("so_khung")), key(f.get("so_may")), key(f.get("cccd"))
    out: list[dict] = []
    seen: set[tuple] = set()

    def add(level, kind, field, msg, c):
        if (kind, c["id"]) not in seen:
            seen.add((kind, c["id"]))
            out.append({"level": level, "kind": kind, "field": field, "msg": msg, "contract": _brief(c, local)})

    for r in con.execute("SELECT * FROM contracts WHERE id IS NOT ? AND status<>'huy'", (exclude_id,)).fetchall():
        c = _view(r)
        active = c["status"] == "dang_cam"
        where = f"HĐ {c['ma']} (hạn {c['den_ngay_vn'] or '?'})"
        for fld, mine, theirs, label in (("so_khung", kk, r["khung_k"], "số khung"), ("so_may", mk, r["may_k"], "số máy"), ("bks", bk, r["bks_k"], "biển số")):
            if not mine or not theirs:
                continue
            if mine == theirs:
                if active:
                    add("high", f"{fld}_active", fld, f"Trùng {label} với {where} — xe này ĐANG CẦM, chưa chuộc.", c)
                else:
                    add("info", f"{fld}_past", fld, f"Trùng {label} với {where} — từng cầm ({'đã chuộc' if c['status'] == 'da_chuoc' else 'đã thanh lý'}).", c)
            elif fld != "bks" and len(mine) >= NEAR_MIN_LEN and near(mine, theirs):
                add("high" if active else "warn", f"{fld}_near", fld,
                    f"{label.capitalize()} gần giống {where} (khác 1 ký tự) — OCR đọc sai hay xe khác? So lại với cà vẹt.", c)
        if ck and ck == r["cccd_k"] and active:
            same = not f.get("ho_ten") or key(c["ho_ten"]) == key(f.get("ho_ten"))
            if same:
                add("info", "cccd_active", "cccd", f"Khách này đang có {where} chưa chuộc.", c)
            else:
                add("warn", "cccd_name", "cccd", f"CCCD trùng {where} nhưng HỌ TÊN khác ('{c['ho_ten']}').", c)
        # cùng biển số nhưng khung khác (hoặc ngược lại) → nhập/đọc sai hoặc giấy tờ giả
        if bk and bk == r["bks_k"] and kk and r["khung_k"] and kk != r["khung_k"] and not near(kk, r["khung_k"]):
            add("warn", "bks_khung_lech", "so_khung", f"Cùng biển số với {where} nhưng SỐ KHUNG khác — kiểm tra lại cà vẹt.", c)
        if kk and kk == r["khung_k"] and bk and r["bks_k"] and bk != r["bks_k"]:
            add("warn", "khung_bks_lech", "bks", f"Cùng số khung với {where} nhưng BIỂN SỐ khác — kiểm tra lại cà vẹt.", c)
    order = {"high": 0, "warn": 1, "info": 2}
    out.sort(key=lambda w: (order[w["level"]], w["kind"]))
    return out


def check(f: dict, local: bool = True) -> list[dict]:
    with connect() as con:
        return find_duplicates(con, f, None, local)


# ---------- ghi ----------
def _ma(con, now: datetime) -> str:
    """Mã HĐ = DDMMYYYY-0000: ngày tạo + số thứ tự trong ngày (bắt đầu lại từ 0001 mỗi ngày)."""
    prefix = now.strftime("%d%m%Y")
    n = con.execute("SELECT COUNT(*) FROM contracts WHERE ma LIKE ?", (f"{prefix}-%",)).fetchone()[0] + 1
    while con.execute("SELECT 1 FROM contracts WHERE ma=?", (f"{prefix}-{n:04d}",)).fetchone():
        n += 1
    return f"{prefix}-{n:04d}"


def create(f: dict, now: datetime | None = None, local: bool = True) -> dict:
    """Lưu hợp đồng. Cùng khách + xe + ngày + số tiền (in lại / bấm 2 lần) → trả lại hợp đồng cũ, không tạo trùng."""
    now = now or datetime.now()
    bk, kk, mk, ck = key(f.get("bks")), key(f.get("so_khung")), key(f.get("so_may")), key(f.get("cccd"))
    if not (bk or kk or mk):
        raise ValueError("Thiếu biển số/số khung/số máy")
    tu = parse_vn(f.get("tu_ngay")) or now.date()
    days = max(money(f.get("so_ngay")), 0)
    den = tu + timedelta(days=days)
    dedupe = "|".join((ck, bk, kk, tu.isoformat(), str(money(f.get("so_tien")))))
    with connect() as con:
        old = con.execute("SELECT * FROM contracts WHERE dedupe=?", (dedupe,)).fetchone()
        if old:
            return {"contract": _view(old), "duplicate": True, "warnings": []}
        warns = find_duplicates(con, f, None, local)
        vals = {k: str(f.get(k) or "").strip()[:300] for k in TEXT_FIELDS}
        cur = con.execute(
            "INSERT INTO contracts(ma,created_at,status,ho_ten,cccd,ngay_cap,dia_chi,sdt,bks,nhan_hieu,so_loai,so_khung,so_may,mau,"
            "so_tien,le_phi,so_ngay,tu_ngay,den_ngay,bks_k,khung_k,may_k,cccd_k,ten_k,dedupe,nguon) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (_ma(con, now), now.isoformat(timespec="seconds"), "dang_cam", vals["ho_ten"], vals["cccd"], vals["ngay_cap"], vals["dia_chi"],
             vals["sdt"], vals["bks"], vals["nhan_hieu"], vals["so_loai"], vals["so_khung"], vals["so_may"], vals["mau"],
             money(f.get("so_tien")), money(f.get("le_phi")), days, tu.isoformat(), den.isoformat(), bk, kk, mk, ck, key(f.get("ho_ten")), dedupe, "may_tinh" if local else "dien_thoai"))
        cid = cur.lastrowid
        con.execute("INSERT INTO events(contract_id,at,type,days,amount,den_ngay,note) VALUES(?,?,?,?,?,?,?)",
                    (cid, now.isoformat(timespec="seconds"), "tao", days, money(f.get("so_tien")), den.isoformat(), ""))
        return {"contract": _view(con.execute("SELECT * FROM contracts WHERE id=?", (cid,)).fetchone()), "duplicate": False, "warnings": warns}


def _get(con, cid: int) -> sqlite3.Row:
    r = con.execute("SELECT * FROM contracts WHERE id=?", (cid,)).fetchone()
    if not r:
        raise KeyError("Không tìm thấy hợp đồng")
    return r


def detail(cid: int) -> dict:
    with connect() as con:
        r = _get(con, cid)
        ev = [dict(e) | {"at_vn": e["at"][:16].replace("T", " "), "den_ngay_vn": to_vn(e["den_ngay"])}
              for e in con.execute("SELECT * FROM events WHERE contract_id=? ORDER BY id", (cid,))]
        return {"contract": _view(r), "events": ev}


def renew(cid: int, days: int, fee: int = 0, note: str = "", now: datetime | None = None) -> dict:
    """Gia hạn: cộng thêm `days` ngày vào hạn hiện tại (hoặc từ hôm nay nếu đã quá hạn), ghi phí gia hạn."""
    now = now or datetime.now()
    if days <= 0 or days > 3650:
        raise ValueError("Số ngày gia hạn không hợp lệ")
    with connect() as con:
        r = _get(con, cid)
        if r["status"] != "dang_cam":
            raise ValueError("Hợp đồng đã đóng, không gia hạn được")
        base = max(date.fromisoformat(r["den_ngay"]), now.date())
        den = base + timedelta(days=days)
        con.execute("UPDATE contracts SET den_ngay=?, so_ngay=so_ngay+? WHERE id=?", (den.isoformat(), days, cid))
        con.execute("INSERT INTO events(contract_id,at,type,days,amount,den_ngay,note) VALUES(?,?,?,?,?,?,?)",
                    (cid, now.isoformat(timespec="seconds"), "gia_han", days, max(fee, 0), den.isoformat(), note[:300]))
        return {"contract": _view(_get(con, cid))}


def close(cid: int, kind: str, amount: int = 0, note: str = "", now: datetime | None = None) -> dict:
    """Chuộc đồ (kind='chuoc') hoặc thanh lý (kind='thanh_ly')."""
    now = now or datetime.now()
    st = {"chuoc": "da_chuoc", "thanh_ly": "thanh_ly"}.get(kind)
    if not st:
        raise ValueError("Loại đóng không hợp lệ")
    with connect() as con:
        r = _get(con, cid)
        if r["status"] != "dang_cam":
            raise ValueError("Hợp đồng đã đóng trước đó")
        con.execute("UPDATE contracts SET status=?, closed_at=?, closed_amount=?, note=CASE WHEN ?<>'' THEN ? ELSE note END WHERE id=?",
                    (st, now.isoformat(timespec="seconds"), max(amount, 0), note[:300], note[:300], cid))
        con.execute("INSERT INTO events(contract_id,at,type,amount,note) VALUES(?,?,?,?,?)",
                    (cid, now.isoformat(timespec="seconds"), kind, max(amount, 0), note[:300]))
        return {"contract": _view(_get(con, cid))}


def reopen(cid: int, now: datetime | None = None) -> dict:
    """Hoàn tác nhầm tay (bấm chuộc nhầm): đưa về 'đang cầm', ghi sự kiện."""
    now = now or datetime.now()
    with connect() as con:
        r = _get(con, cid)
        if r["status"] == "dang_cam":
            raise ValueError("Hợp đồng đang mở")
        if r["status"] == "huy":
            raise ValueError("Hợp đồng đã hủy, không mở lại được")
        con.execute("UPDATE contracts SET status='dang_cam', closed_at=NULL, closed_amount=NULL WHERE id=?", (cid,))
        con.execute("INSERT INTO events(contract_id,at,type,note) VALUES(?,?,?,?)", (cid, now.isoformat(timespec="seconds"), "mo_lai", "Hoàn tác"))
        return {"contract": _view(_get(con, cid))}


def set_note(cid: int, note: str) -> dict:
    with connect() as con:
        _get(con, cid)
        con.execute("UPDATE contracts SET note=? WHERE id=?", (note[:500], cid))
        return {"contract": _view(_get(con, cid))}


# ---------- tra cứu / thống kê ----------
def search(q: str = "", status: str = "", limit: int = 100, offset: int = 0, today: date | None = None) -> dict:
    today = today or date.today()
    k, digits, up = key(q), re.sub(r"\D", "", q or ""), (q or "").strip().upper()
    where, args = ([] if "huy" in status.split(",") else ["status<>'huy'"]), []
    if k:       # khớp biển số/khung/máy/CCCD/tên (đều đã chuẩn hoá, không dấu) / SĐT / mã HĐ
        ors, a = ["bks_k LIKE ?", "khung_k LIKE ?", "may_k LIKE ?", "cccd_k LIKE ?", "ten_k LIKE ?", "ma LIKE ?"], [f"%{k}%"] * 5 + [f"%{up}%"]
        if len(digits) >= 3:
            ors.append("sdt LIKE ?"); a.append(f"%{digits}%")
        where.append("(" + " OR ".join(ors) + ")"); args += a
    iso = today.isoformat()
    soon = (today + timedelta(days=SOON_DAYS)).isoformat()
    ors = []                      # status nhận nhiều trạng thái, cách nhau dấu phẩy (chọn nhiều) → hợp bằng OR
    for st in [x for x in status.split(",") if x]:
        if st == "qua_han":
            ors.append("(status='dang_cam' AND den_ngay < ?)"); args.append(iso)
        elif st == "sap_han":
            ors.append("(status='dang_cam' AND den_ngay >= ? AND den_ngay <= ?)"); args += [iso, soon]
        elif st in STATUSES:
            ors.append("status=?"); args.append(st)
    if ors:
        where.append("(" + " OR ".join(ors) + ")")
    sql = "FROM contracts" + (" WHERE " + " AND ".join(where) if where else "")
    with connect() as con:
        total = con.execute("SELECT COUNT(*) " + sql, args).fetchone()[0]
        rows = con.execute("SELECT * " + sql + " ORDER BY CASE status WHEN 'dang_cam' THEN 0 ELSE 1 END, den_ngay, id DESC LIMIT ? OFFSET ?",
                           args + [max(min(limit, 500), 1), max(offset, 0)]).fetchall()
        return {"total": total, "items": [_view(r, today) for r in rows]}


def stats(today: date | None = None, remote: bool = False) -> dict:
    """Số liệu thẻ đầu trang Hợp đồng. remote=True (điện thoại sau khi nhập PIN): chỉ số lượng, KHÔNG có tiền."""
    today = today or date.today()
    iso, soon, m0 = today.isoformat(), (today + timedelta(days=SOON_DAYS)).isoformat(), today.replace(day=1).isoformat()
    with connect() as con:
        q = lambda sql, *a: con.execute(sql, a).fetchone()
        act = q("SELECT COUNT(*) n, COALESCE(SUM(so_tien),0) v FROM contracts WHERE status='dang_cam'")
        out = {
            "dang_cam": act["n"],
            "qua_han": q("SELECT COUNT(*) FROM contracts WHERE status='dang_cam' AND den_ngay < ?", iso)[0],
            "sap_han": q("SELECT COUNT(*) FROM contracts WHERE status='dang_cam' AND den_ngay>=? AND den_ngay<=?", iso, soon)[0],
            "da_chuoc": q("SELECT COUNT(*) FROM contracts WHERE status='da_chuoc'")[0],
            "thanh_ly": q("SELECT COUNT(*) FROM contracts WHERE status='thanh_ly'")[0],
        }
        if remote:
            return out
        rp = _period(con, m0, (today + timedelta(days=1)).isoformat())
        out.update({
            "von_dang_cam": act["v"],
            "moi_thang": q("SELECT COUNT(*) FROM contracts WHERE status<>'huy' AND substr(created_at,1,10) >= ?", m0)[0],
            "von_moi_thang": rp["cho_cam_moi"],
            "doanh_thu_thang": rp["doanh_thu"],
            "sao_luu": last_backup(),
            "sao_luu_ngoai": offsite_status(),
        })
        return out


# ---------- báo cáo vốn / doanh thu / lợi nhuận ----------
# QUY TẮC (theo mẫu hợp đồng của tiệm — xem ô '?' trên giao diện):
#  • Vốn đang bỏ ra  = tổng TIỀN GỐC (so_tien) của hợp đồng đang cầm.
#  • Doanh thu       = lệ phí lúc lập hợp đồng (tính theo ngày lập) + lệ phí các lần gia hạn (theo ngày thu)
#                      + phần khách trả vượt tiền gốc khi chuộc (lệ phí còn nợ, theo ngày chuộc).
#  • Chuộc: khách trả lại gốc = THU HỒI VỐN, không phải doanh thu.
#  • Thanh lý: lãi/lỗ = giá bán − tiền gốc (theo ngày thanh lý). Chưa nhập giá bán (0/trống) → không tính.
#  • Lợi nhuận       = doanh thu + lãi/lỗ thanh lý.
#  • Hợp đồng đã HỦY bị loại khỏi mọi con số. Chuộc/thanh lý tính theo TRẠNG THÁI HIỆN TẠI của hợp đồng
#    (không cộng theo sự kiện) nên 'mở lại' tự động bỏ khoản đó.
def _period(con, frm: str, to: str) -> dict:
    """Số liệu trong [frm, to) — ngày ISO. to là mốc loại trừ."""
    one = lambda sql, *a: con.execute(sql, a).fetchone()[0]
    created = "status<>'huy' AND substr(created_at,1,10) >= ? AND substr(created_at,1,10) < ?"
    r = {
        "cho_cam_moi": one(f"SELECT COALESCE(SUM(so_tien),0) FROM contracts WHERE {created}", frm, to),
        "le_phi_tao": one(f"SELECT COALESCE(SUM(le_phi),0) FROM contracts WHERE {created}", frm, to),
        "le_phi_gia_han": one("SELECT COALESCE(SUM(e.amount),0) FROM events e JOIN contracts c ON c.id=e.contract_id "
                              "WHERE e.type='gia_han' AND c.status<>'huy' AND substr(e.at,1,10) >= ? AND substr(e.at,1,10) < ?", frm, to),
    }
    closed = "status=? AND substr(closed_at,1,10) >= ? AND substr(closed_at,1,10) < ?"
    chuoc = con.execute(f"SELECT so_tien, closed_amount FROM contracts WHERE {closed}", ("da_chuoc", frm, to)).fetchall()
    goc = fee = 0
    for c in chuoc:
        tra = c["so_tien"] if c["closed_amount"] is None else c["closed_amount"]
        goc += min(tra, c["so_tien"]); fee += max(tra - c["so_tien"], 0)
    r.update(so_chuoc=len(chuoc), thu_hoi_goc=goc, le_phi_chuoc=fee)
    tl = con.execute(f"SELECT so_tien, closed_amount FROM contracts WHERE {closed}", ("thanh_ly", frm, to)).fetchall()
    r["so_thanh_ly"] = len(tl)
    r["thanh_ly_chua_gia"] = sum(1 for c in tl if not c["closed_amount"])
    r["lai_lo_thanh_ly"] = sum(c["closed_amount"] - c["so_tien"] for c in tl if c["closed_amount"])
    r["doanh_thu"] = r["le_phi_tao"] + r["le_phi_gia_han"] + r["le_phi_chuoc"]
    r["loi_nhuan"] = r["doanh_thu"] + r["lai_lo_thanh_ly"]
    return r


def report(frm: str = "", to: str = "", today: date | None = None) -> dict:
    """Báo cáo khoảng [frm, to] (ISO, gồm cả hai đầu). Mặc định: tháng hiện tại. Kèm lợi nhuận 6 tháng gần nhất."""
    today = today or date.today()
    try:
        a = date.fromisoformat(frm) if frm else today.replace(day=1)
        b = date.fromisoformat(to) if to else today
    except ValueError:
        raise ValueError("Ngày không hợp lệ")
    if b < a:
        raise ValueError("Khoảng ngày không hợp lệ")
    with connect() as con:
        cur = _period(con, a.isoformat(), (b + timedelta(days=1)).isoformat())
        v = con.execute("SELECT COUNT(*) n, COALESCE(SUM(so_tien),0) v FROM contracts WHERE status='dang_cam'").fetchone()
        cur.update(von_dang_cam=v["v"], so_dang_cam=v["n"], tu=a.isoformat(), den=b.isoformat(),
                   ty_suat=round(cur["loi_nhuan"] * 100 / v["v"], 1) if v["v"] else 0.0)
        series, m = [], today.replace(day=1)
        for _ in range(6):
            nxt = (m.replace(day=28) + timedelta(days=4)).replace(day=1)
            series.append({"thang": m.strftime("%m/%Y"), "loi_nhuan": _period(con, m.isoformat(), nxt.isoformat())["loi_nhuan"]})
            m = (m - timedelta(days=1)).replace(day=1)
        cur["chuoi"] = series[::-1]
        return cur


# ---------- sửa / hủy hợp đồng ----------
EDITABLE = ("ho_ten", "cccd", "ngay_cap", "dia_chi", "sdt", "bks", "nhan_hieu", "so_loai", "so_khung", "so_may", "mau")


def update(cid: int, f: dict, now: datetime | None = None) -> dict:
    """Sửa thông tin (nhập sai). Ghi sự kiện 'sua' kèm giá trị cũ → mới. Hợp đồng đã hủy không sửa được."""
    now = now or datetime.now()
    with connect() as con:
        r = _get(con, cid)
        if r["status"] == "huy":
            raise ValueError("Hợp đồng đã hủy, không sửa được")
        new, changes = {}, []
        for k in EDITABLE:
            if k in f:
                v = str(f[k] or "").strip()[:300]
                if v != (r[k] or ""):
                    new[k] = v; changes.append(f"{k}: {r[k] or ''} → {v}")
        for k in ("so_tien", "le_phi"):
            if k in f and f[k] not in (None, ""):
                v = money(f[k])
                if v != (r[k] or 0):
                    new[k] = v; changes.append(f"{k}: {r[k] or 0} → {v}")
        if not new:
            return {"contract": _view(r)}
        m = {**dict(r), **new}
        bk, kk, mk, ck = key(m["bks"]), key(m["so_khung"]), key(m["so_may"]), key(m["cccd"])
        if not (bk or kk or mk):
            raise ValueError("Thiếu biển số/số khung/số máy")
        dedupe = r["dedupe"] if r["status"] == "huy" else "|".join((ck, bk, kk, r["tu_ngay"], str(m["so_tien"] or 0)))
        sets = ", ".join(f"{k}=?" for k in new) + ", bks_k=?, khung_k=?, may_k=?, cccd_k=?, ten_k=?, dedupe=?"
        try:
            con.execute(f"UPDATE contracts SET {sets} WHERE id=?", [*new.values(), bk, kk, mk, ck, key(m["ho_ten"]), dedupe, cid])
        except sqlite3.IntegrityError:
            raise ValueError("Trùng với một hợp đồng khác (cùng khách, xe, ngày và số tiền)")
        con.execute("INSERT INTO events(contract_id,at,type,note) VALUES(?,?,?,?)", (cid, now.isoformat(timespec="seconds"), "sua", "; ".join(changes)[:500]))
        return {"contract": _view(_get(con, cid))}


def cancel(cid: int, reason: str, now: datetime | None = None) -> dict:
    """Hủy hợp đồng lập nhầm/trùng: không xóa (để truy vết) nhưng loại khỏi mọi danh sách, cảnh báo trùng và số liệu."""
    now = now or datetime.now()
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Cần nhập lý do hủy")
    with connect() as con:
        r = _get(con, cid)
        if r["status"] == "huy":
            raise ValueError("Hợp đồng đã hủy trước đó")
        con.execute("UPDATE contracts SET status='huy', closed_at=?, dedupe=? WHERE id=?", (now.isoformat(timespec="seconds"), f"huy:{cid}", cid))
        con.execute("INSERT INTO events(contract_id,at,type,note) VALUES(?,?,?,?)", (cid, now.isoformat(timespec="seconds"), "huy", reason[:300]))
        return {"contract": _view(_get(con, cid))}


def delete_hard(cid: int) -> str:
    """Xóa hẳn hợp đồng + lịch sử (dùng khi thử nghiệm). Trả mã hợp đồng để xóa ảnh kèm theo."""
    with connect() as con:
        ma = _get(con, cid)["ma"]
        con.execute("DELETE FROM events WHERE contract_id=?", (cid,))
        con.execute("DELETE FROM contracts WHERE id=?", (cid,))
    return ma


def export_csv() -> str:
    cols = ("ma", "created_at", "status", "ho_ten", "cccd", "ngay_cap", "dia_chi", "sdt", "bks", "nhan_hieu", "so_loai", "so_khung", "so_may",
            "mau", "so_tien", "le_phi", "so_ngay", "tu_ngay", "den_ngay", "closed_at", "closed_amount", "note")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    with connect() as con:
        for r in con.execute("SELECT * FROM contracts ORDER BY id"):
            w.writerow([("'" + str(r[c]) if c in ("cccd", "sdt") and r[c] else r[c]) for c in cols])   # dấu ' để Excel không biến CCCD/SĐT thành số
    return "﻿" + buf.getvalue()


# ---------- sao lưu ----------
BACKUP_DIR = DB_PATH.parent / "backup"
KEEP_BACKUPS = 30


def backup(now: datetime | None = None) -> Path | None:
    """Sao lưu nóng (API backup của SQLite, an toàn khi đang ghi) ra data/backup/contracts-YYYYMMDD.db; giữ 30 bản gần nhất.
    Mỗi ngày 1 bản (gọi lại trong ngày thì ghi đè bản của ngày đó). Không có DB thì bỏ qua."""
    now = now or datetime.now()
    if not DB_PATH.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / f"contracts-{now:%Y%m%d}.db"
    with connect() as con:
        out = sqlite3.connect(dest)
        try:
            con.backup(out)
        finally:
            out.close()
    for old in sorted(BACKUP_DIR.glob("contracts-*.db"))[:-KEEP_BACKUPS]:
        old.unlink(missing_ok=True)
    offsite_copy(dest)
    return dest


# ---- Sao lưu ra ngoài máy (Google Drive for desktop / USB / ổ mạng) ----
OFFSITE_CFG = DB_PATH.parent / "offsite.json"
_offsite_err = ""


def detect_offsite() -> str:
    """Tự tìm thư mục để chép bản sao lưu ra ngoài máy: Google Drive / OneDrive / USB. Không thấy thì trả ''."""
    home = Path.home()
    cands: list[Path] = []
    if os.name == "nt":
        for L in "DEFGHIJKLMNOPQRSTUVWXYZ":
            for sub in ("My Drive", "Google Drive", "Drive của tôi"):
                cands.append(Path(f"{L}:/{sub}"))
        cands += [home / "Google Drive", home / "My Drive"] + sorted(home.glob("OneDrive*"))
        try:
            import ctypes
            mask = ctypes.windll.kernel32.GetLogicalDrives()
            for i, L in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
                if mask >> i & 1 and L not in "AC" and ctypes.windll.kernel32.GetDriveTypeW(f"{L}:\\") == 2:   # 2 = ổ cắm ngoài (USB)
                    cands.append(Path(f"{L}:/"))
        except Exception:
            pass
    else:
        cs = home / "Library" / "CloudStorage"
        if cs.is_dir():
            cands += sorted(cs.glob("GoogleDrive-*/My Drive")) + sorted(cs.glob("OneDrive*"))
        cands += [home / "Google Drive", home / "OneDrive"]
        vol = Path("/Volumes")
        if vol.is_dir():
            cands += [v for v in sorted(vol.iterdir()) if v.is_dir() and not v.is_symlink()]
    for d in cands:
        try:
            if d.is_dir() and os.access(d, os.W_OK):
                return str(d)
        except OSError:
            continue
    return ""


_auto_cache: tuple[float, str] = (0.0, "")


def offsite_path() -> str:
    """Thư mục sao lưu ngoài: do người dùng đặt tay (ưu tiên) hoặc tự dò."""
    global _auto_cache
    try:
        v = json.loads(OFFSITE_CFG.read_text("utf-8")).get("path", "")
        if v:
            return v
    except Exception:
        pass
    import time
    if time.time() - _auto_cache[0] > 600:
        _auto_cache = (time.time(), detect_offsite())
    return _auto_cache[1]


def set_offsite(path: str) -> dict:
    """Đặt tay thư mục sao lưu ngoài ('' = quay về tự dò). Thư mục phải tồn tại và ghi được; chép thử 1 bản ngay."""
    global _auto_cache
    path = (path or "").strip().strip('"')
    if path:
        d = Path(path).expanduser()
        if not d.is_dir():
            raise ValueError("Thư mục không tồn tại (cắm USB / mở Google Drive trước).")
        try:
            t = d / ".scanapp-test"
            t.write_text("ok")
            t.unlink()
        except OSError:
            raise ValueError("Không ghi được vào thư mục này.")
    OFFSITE_CFG.parent.mkdir(parents=True, exist_ok=True)
    OFFSITE_CFG.write_text(json.dumps({"path": path}), "utf-8")
    _auto_cache = (0.0, "")
    return {"path": offsite_path(), "ok": offsite_copy_latest() if offsite_path() else True}


def offsite_copy(src: Path) -> bool:
    """Chép 1 bản ra thư mục ngoài; lỗi (USB rút, Drive chưa mở) thì ghi nhận, không làm hỏng sao lưu chính."""
    global _offsite_err
    d = offsite_path()
    if not d:
        _offsite_err = "Chưa tìm thấy Google Drive, OneDrive hoặc USB"
        return False
    try:
        out = Path(d) / "ScanApp-backup"
        out.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out / src.name)
        for old in sorted(out.glob("contracts-*.db"))[:-KEEP_BACKUPS]:
            old.unlink(missing_ok=True)
        _offsite_err = ""
        return True
    except OSError as e:
        _offsite_err = str(e)
        return False


def offsite_copy_latest() -> bool:
    files = sorted(BACKUP_DIR.glob("contracts-*.db")) if BACKUP_DIR.exists() else []
    return offsite_copy(files[-1]) if files else False


def offsite_status(now: datetime | None = None) -> dict:
    """path: nơi đang chép ra ngoài ('' = chưa có). warn: True khi chưa có bản ngoài nào mới hơn 2 ngày."""
    now = now or datetime.now()
    d = offsite_path()
    last = ""
    warn = True
    if d:
        files = sorted((Path(d) / "ScanApp-backup").glob("contracts-*.db")) if (Path(d) / "ScanApp-backup").is_dir() else []
        if files:
            t = datetime.fromtimestamp(files[-1].stat().st_mtime)
            last, warn = t.strftime("%d/%m/%Y %H:%M"), (now - t) > timedelta(days=2)
    return {"path": d, "error": _offsite_err, "last": last, "warn": warn}


# ---- Danh sách bản sao lưu + khôi phục ----
_BK_RE = re.compile(r"contracts-\d{8}\.db")


def closed_for_cleanup() -> list[tuple[str, str]]:
    with connect() as con:
        return [(r["ma"], r["closed_at"]) for r in con.execute("SELECT ma, closed_at FROM contracts WHERE status<>'dang_cam' AND closed_at IS NOT NULL")]


def list_backups() -> list[dict]:
    out = []
    for f in sorted(BACKUP_DIR.glob("contracts-*.db"), reverse=True)[:15] if BACKUP_DIR.exists() else []:
        try:
            c = sqlite3.connect(f"file:{f}?mode=ro", uri=True)
            n = c.execute("SELECT COUNT(*) FROM contracts WHERE status<>'huy'").fetchone()[0]
            c.close()
        except sqlite3.Error:
            continue
        out.append({"name": f.name, "at": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%Y %H:%M"), "hop_dong": n, "kb": round(f.stat().st_size / 1024)})
    return out


def restore(name: str, now: datetime | None = None) -> dict:
    """Khôi phục DB từ 1 bản sao lưu. Trước đó tự sao lưu bản hiện tại (truoc-khoi-phuc-*.db) để quay lại được."""
    now = now or datetime.now()
    if not _BK_RE.fullmatch(name or ""):
        raise ValueError("Tên bản sao lưu không hợp lệ")
    src = BACKUP_DIR / name
    if not src.is_file():
        raise ValueError("Không thấy bản sao lưu này")
    try:
        t = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
        t.execute("SELECT COUNT(*) FROM contracts").fetchone()
        t.close()
    except sqlite3.Error:
        raise ValueError("Bản sao lưu bị hỏng, không dùng được")
    keep = BACKUP_DIR / f"truoc-khoi-phuc-{now:%Y%m%d-%H%M%S}.db"
    with connect() as con:
        out = sqlite3.connect(keep)
        try:
            con.backup(out)
        finally:
            out.close()
        s = sqlite3.connect(src)
        try:
            s.backup(con)
        finally:
            s.close()
    for old in sorted(BACKUP_DIR.glob("truoc-khoi-phuc-*.db"))[:-5]:
        old.unlink(missing_ok=True)
    return {"ok": True, "giu_ban_cu": keep.name}


def last_backup() -> str:
    files = sorted(BACKUP_DIR.glob("contracts-*.db")) if BACKUP_DIR.exists() else []
    return datetime.fromtimestamp(files[-1].stat().st_mtime).strftime("%d/%m/%Y %H:%M") if files else ""
