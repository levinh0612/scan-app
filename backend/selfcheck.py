"""Kiểm tra nhanh trước khi (re)start server. Dùng chung cho run.sh và run.ps1. Thoát != 0 nếu lỗi."""
import compileall
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")
here = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(here))

if not compileall.compile_dir(str(here), quiet=1, force=True):
    print("   LỖI cú pháp trong backend/")
    sys.exit(1)

import importlib  # noqa: E402

total = 0
for path in sorted(here.glob("test_*.py")):
    mod = importlib.import_module(path.stem)
    for n in [n for n in dir(mod) if n.startswith("test_")]:
        getattr(mod, n)()
        total += 1
print(f"   test: {total}/{total} đạt" if total else "   test: (không có file test trên máy này — chỉ kiểm cú pháp + import)")

import app  # noqa: E402,F401  (kiểm tra thư viện cài đủ; chưa nạp model OCR)

print("   import app: OK")
