"""Tạo chứng chỉ https tự ký cho mạng nội bộ (để điện thoại mở được camera).
Dùng:  python backend/make_cert.py <IP-LAN> [thư-mục-ra]   → in đường dẫn cert, key.
Tạo lại khi IP đổi hoặc sắp hết hạn; còn hợp lệ thì giữ nguyên (điện thoại không phải bấm 'tiếp tục' lại)."""
from __future__ import annotations

import datetime as dt
import ipaddress
import pathlib
import sys

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def ensure(ip: str | None, out: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    out.mkdir(parents=True, exist_ok=True)
    crt, key = out / "local.crt", out / "local.key"
    want = {"127.0.0.1"} | ({ip} if ip else set())
    if crt.exists() and key.exists():
        try:
            c = x509.load_pem_x509_certificate(crt.read_bytes())
            have = {str(i) for i in c.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.IPAddress)}
            c.extensions.get_extension_for_class(x509.ExtendedKeyUsage)   # cert cũ thiếu EKU → ném lỗi → tạo lại
            if want <= have and c.not_valid_after_utc > dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=30):
                return crt, key
        except Exception:
            pass
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "scan-app (noi bo)")])
    san = [x509.DNSName("localhost")] + [x509.IPAddress(ipaddress.ip_address(a)) for a in sorted(want)]
    now = dt.datetime.now(dt.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(k.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - dt.timedelta(days=1))
            .not_valid_after(now + dt.timedelta(days=397))
            .add_extension(x509.SubjectAlternativeName(san), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True, key_encipherment=True, content_commitment=False, data_encipherment=False,
                                         key_agreement=False, key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)   # iOS/Safari đòi dấu "dùng cho máy chủ web"
            .sign(k, hashes.SHA256()))
    crt.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key.write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
    try:
        key.chmod(0o600)
    except OSError:
        pass
    return crt, key


if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else None
    out = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path(__file__).resolve().parent.parent / ".run" / "cert"
    c, k = ensure(ip, out)
    print(c)
    print(k)
