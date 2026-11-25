"""Hàng đợi lệnh in dùng chung giữa điện thoại và máy tính. Chỉ lưu trong RAM (mất khi restart),
tự xoá sau 12 giờ, tối đa 30 lệnh. Bản chụp dữ liệu (snapshot) chỉ dùng để 'In lại'."""
from __future__ import annotations

import secrets
import threading
import time

STATUSES = {"cho_in", "dang_in", "da_gui", "da_ra_giay", "loi"}
TTL_SECONDS = 12 * 3600
MAX_JOBS = 30
MAX_KEYS = 40
MAX_LEN = 500


def clean_snapshot(snap) -> dict[str, str]:
    """Chỉ giữ cặp chuỗi→chuỗi, giới hạn kích thước (dữ liệu đến từ trình duyệt, không tin tưởng)."""
    if not isinstance(snap, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in list(snap.items())[:MAX_KEYS]:
        if isinstance(k, str) and isinstance(v, (str, int, float)):
            out[k[:40]] = str(v)[:MAX_LEN]
    return out


class JobStore:
    def __init__(self, clock=time.time):
        self._clock = clock
        self._lock = threading.Lock()
        self._jobs: dict[str, dict] = {}

    def _prune(self) -> None:
        now = self._clock()
        for jid in [j for j, v in self._jobs.items() if now - v["updated"] > TTL_SECONDS]:
            del self._jobs[jid]
        while len(self._jobs) > MAX_JOBS:
            del self._jobs[min(self._jobs, key=lambda j: self._jobs[j]["created"])]

    @staticmethod
    def _public(job: dict) -> dict:
        return {k: v for k, v in job.items() if k != "snapshot"}

    def create(self, bks: str, xe: str, chu: str, snapshot, status: str = "cho_in") -> dict:
        if status not in STATUSES:
            raise ValueError("Trạng thái không hợp lệ")
        with self._lock:
            now = self._clock()
            job = {"id": f"J{secrets.token_hex(5)}", "bks": str(bks)[:30], "xe": str(xe)[:60], "chu": str(chu)[:80],
                   "status": status, "created": now, "updated": now,
                   "lan": 1 if status == "dang_in" else 0, "note": "", "snapshot": clean_snapshot(snapshot)}
            self._jobs[job["id"]] = job
            self._prune()
            return self._public(job)

    def list(self) -> list[dict]:
        with self._lock:
            self._prune()
            return [self._public(j) for j in sorted(self._jobs.values(), key=lambda j: -j["created"])]

    def snapshot(self, jid: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(jid)
            return dict(job["snapshot"]) if job else None

    def update(self, jid: str, status: str, note: str = "") -> dict | None:
        if status not in STATUSES:
            raise ValueError("Trạng thái không hợp lệ")
        with self._lock:
            job = self._jobs.get(jid)
            if not job:
                return None
            job["status"], job["updated"], job["note"] = status, self._clock(), str(note)[:300]
            if status == "dang_in":
                job["lan"] += 1
            return self._public(job)

    def delete(self, jid: str) -> bool:
        with self._lock:
            return self._jobs.pop(jid, None) is not None
