"""T-27: chứng chỉ HTTPS tự ký cho môi trường chạy thử.

Mã hóa TLS đặt ở cửa vào của trình duyệt (Vite :5500, xem frontend/vite.config.ts); khi đã có chứng chỉ,
run.py cho API chỉ nghe 127.0.0.1 nên không gọi thẳng được API qua HTTP dạng rõ từ máy khác.
Triển khai thật: thay bằng reverse proxy (nginx/Caddy) với chứng chỉ do CA cấp (VD Let's Encrypt).

  python -m security.tls                       # tạo data/certs/cert.pem + key.pem cho localhost
  python -m security.tls --host 192.168.1.10   # thêm IP/tên máy để máy khác trong mạng truy cập
Trình duyệt sẽ cảnh báo vì chứng chỉ tự ký: chấp nhận một lần, hoặc nhập cert.pem vào
"Trusted Root Certification Authorities" (certmgr.msc) trên máy dùng thử.
"""
from __future__ import annotations

import ipaddress
import sys
from datetime import datetime, timedelta, timezone

from pipeline import DATA_DIR

CERT_DIR = DATA_DIR / "certs"
CERT, KEY = CERT_DIR / "cert.pem", CERT_DIR / "key.pem"
DAYS = 365


def generate(hosts: list[str]) -> None:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    names: list[x509.GeneralName] = []
    for h in ["localhost", "127.0.0.1", *hosts]:
        try:
            names.append(x509.IPAddress(ipaddress.ip_address(h)))
        except ValueError:
            names.append(x509.DNSName(h))
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "sss-dev"),
                         x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Social Sentiment System (chạy thử)")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=DAYS))
            .add_extension(x509.SubjectAlternativeName(names), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True, key_encipherment=False, content_commitment=False, data_encipherment=False,
                                         key_agreement=True, key_cert_sign=False, crl_sign=False, encipher_only=False,
                                         decipher_only=False), critical=True)
            .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(key, hashes.SHA256()))
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    KEY.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    CERT.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def enabled() -> bool:
    return CERT.exists() and KEY.exists()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    hosts = [args[i + 1] for i, a in enumerate(args) if a == "--host" and i + 1 < len(args)]
    generate(hosts)
    print(f"Đã tạo {CERT} và {KEY} (hạn {DAYS} ngày) cho: localhost, 127.0.0.1{''.join(', ' + h for h in hosts)}")
    print("Chạy lại frontend (npm run dev) rồi mở https://localhost:5500")
