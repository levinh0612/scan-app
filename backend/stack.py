"""Gộp nhiều khung hình liên tiếp thành một ảnh: chọn khung nét nhất làm gốc, căn chỉnh các khung còn lại theo nó (ECC),
lấy trung bình có trọng số độ nét → giảm nhiễu/vân sọc, chữ mờ do rung tay rõ hơn. Không bịa nét chữ (khác AI siêu phân giải)."""
from __future__ import annotations

import cv2
import numpy as np


def sharpness(img: np.ndarray) -> float:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(g, cv2.CV_64F).var())


def _align(ref_g: np.ndarray, g: np.ndarray, size: tuple[int, int]):
    """Ma trận affine đưa `g` về khớp `ref_g` (tính trên ảnh thu nhỏ, trả về đã quy về cỡ gốc) hoặc None nếu không khớp được."""
    h, w = ref_g.shape
    k = 0.5
    a = cv2.resize(ref_g, None, fx=k, fy=k, interpolation=cv2.INTER_AREA).astype(np.float32)
    b = cv2.resize(g, None, fx=k, fy=k, interpolation=cv2.INTER_AREA).astype(np.float32)
    a, b = cv2.GaussianBlur(a, (0, 0), 1.2), cv2.GaussianBlur(b, (0, 0), 1.2)
    m = np.eye(2, 3, dtype=np.float32)
    try:
        cc, m = cv2.findTransformECC(a, b, m, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 60, 1e-5), None, 5)
    except cv2.error:
        return None
    if cc < 0.85:
        return None
    m[:, 2] /= k                                              # phần tịnh tiến về cỡ gốc
    return m


def stack_frames(frames: list[np.ndarray]) -> tuple[np.ndarray, dict]:
    """Trả (ảnh gộp, thông tin). 1 khung → trả nguyên khung đó."""
    if len(frames) == 1:
        return frames[0], {"n": 1, "used": 1}
    h, w = frames[0].shape[:2]
    frames = [f if f.shape[:2] == (h, w) else cv2.resize(f, (w, h)) for f in frames]
    sh = [sharpness(f) for f in frames]
    order = sorted(range(len(frames)), key=lambda i: -sh[i])
    ref = frames[order[0]]
    ref_g = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
    acc = ref.astype(np.float32) * sh[order[0]]
    wsum = sh[order[0]]
    used = 1
    for i in order[1:]:
        if sh[i] < 0.4 * sh[order[0]]:                         # khung quá mờ so với khung tốt nhất: bỏ
            continue
        m = _align(ref_g, cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY), (w, h))
        if m is None:
            continue
        al = cv2.warpAffine(frames[i], m, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
        acc += al.astype(np.float32) * sh[i]
        wsum += sh[i]
        used += 1
    out = np.clip(acc / wsum, 0, 255).astype(np.uint8)
    if used > 1:                                               # trung bình làm mềm nhẹ → làm nét lại một chút
        bl = cv2.GaussianBlur(out, (0, 0), 1.0)
        out = cv2.addWeighted(out, 1.5, bl, -0.5, 0)
    return out, {"n": len(frames), "used": used, "sharp_ref": round(sh[order[0]], 1)}
