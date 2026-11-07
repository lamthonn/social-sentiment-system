"""Chạy toàn bộ dự án trong 1 cửa sổ: PostgreSQL (Docker) -> migrate -> API + frontend.

    python run.py            chạy (tự cài thư viện khi requirements.txt / package-lock.json đổi)
    python run.py install    ép cài lại thư viện Python + frontend

Ctrl+C để dừng tất cả (API, frontend và container DB).
"""
from __future__ import annotations

import hashlib
import os
import socket
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# npm --prefix trên Windows vẫn tìm package.json ở thư mục hiện tại -> chạy npm trong frontend/
FRONTEND = ROOT / "frontend"
IS_WINDOWS = os.name == "nt"
NPM = "npm.cmd" if IS_WINDOWS else "npm"
DOCKER_DESKTOP = Path(r"C:\Program Files\Docker\Docker\Docker Desktop.exe")

# Windows mặc định cp1252 -> lỗi khi in tiếng Việt có dấu, và pip không đọc được
# requirements.txt (comment tiếng Việt). Tiến trình con (pip, uvicorn...) kế thừa biến này.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ["PYTHONUTF8"] = "1"


def step(msg: str) -> None:
    print(f"\n=== {msg} ===", flush=True)


def die(msg: str) -> None:
    print(f"\n[LỖI] {msg}", flush=True)
    sys.exit(1)


def run(*cmd: str, cwd: Path = ROOT) -> None:
    if subprocess.run(cmd, cwd=cwd).returncode != 0:
        die(f"Lệnh thất bại: {' '.join(cmd)}")


def ok(*cmd: str) -> bool:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True).returncode == 0


def wait_until(check, seconds: int, error: str) -> None:
    deadline = time.time() + seconds
    while not check():
        if time.time() > deadline:
            die(error)
        time.sleep(2)


def install_if_changed(manifest: Path, stamp: Path, *cmd: str, force: bool,
                       cwd: Path = ROOT) -> None:
    """Chạy lệnh cài đặt khi file manifest đổi so với lần cài trước (lưu hash vào stamp)."""
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    if not force and stamp.exists() and stamp.read_text() == digest:
        return
    step(f"Cài thư viện ({manifest.relative_to(ROOT)} thay đổi)")
    run(*cmd, cwd=cwd)
    stamp.write_text(digest)


def port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wsl_distros() -> list[str]:
    """Các distro WSL, distro mặc định đứng đầu (wsl.exe in ra UTF-16)."""
    out = subprocess.run(["wsl", "-l", "-q"], capture_output=True).stdout
    return [d.strip() for d in out.decode("utf-16-le", errors="ignore").splitlines() if d.strip()]


def find_docker() -> list[str]:
    """Lệnh docker dùng được: docker trên Windows/Linux, nếu không có thì docker trong WSL
    (distro đầu tiên có `docker compose`; ép distro bằng biến môi trường DOCKER_WSL_DISTRO)."""
    if shutil.which("docker"):
        return ["docker"]
    if IS_WINDOWS and shutil.which("wsl"):
        forced = os.environ.get("DOCKER_WSL_DISTRO")
        for distro in [forced] if forced else wsl_distros():
            cmd = ["wsl", "-d", distro, "--", "docker"]
            if ok(*cmd, "compose", "version"):
                return cmd
    die("Không tìm thấy docker (cả trên Windows lẫn trong WSL).")


def ensure_docker() -> list[str]:
    docker = find_docker()
    if ok(*docker, "info"):
        return docker
    if docker[0] == "wsl":
        print(f"Docker trong WSL ({docker[2]}) chưa chạy, đang bật...", flush=True)
        subprocess.run(["wsl", "-d", docker[2], "-u", "root", "--", "service", "docker", "start"])
    elif IS_WINDOWS and DOCKER_DESKTOP.exists():
        print("Docker chưa chạy, đang mở Docker Desktop...", flush=True)
        subprocess.Popen([str(DOCKER_DESKTOP)])
    wait_until(lambda: ok(*docker, "info"), 120, "Đợi Docker quá 2 phút vẫn chưa sẵn sàng.")
    return docker


def main() -> None:
    if not (ROOT / ".env").exists():
        die("Chưa có .env. Tạo bằng: copy .env.example .env  (rồi sửa mật khẩu, salt)")

    force = "install" in sys.argv[1:]
    install_if_changed(ROOT / "requirements.txt", Path(sys.prefix) / ".requirements.sha256",
                       sys.executable, "-m", "pip", "install", "-r", "requirements.txt", force=force)
    node_modules = FRONTEND / "node_modules"
    install_if_changed(FRONTEND / "package-lock.json", node_modules / ".lock.sha256",
                       NPM, "install", cwd=FRONTEND,
                       force=force or not node_modules.exists())

    step("Bật PostgreSQL + Adminer")
    docker = ensure_docker()
    run(*docker, "compose", "up", "-d")
    wait_until(lambda: ok(*docker, "exec", "sss_postgres", "pg_isready", "-q"), 60,
               "PostgreSQL không sẵn sàng sau 60 giây. Xem: docker logs sss_postgres")

    step("Tạo/nâng cấp bảng")
    run(sys.executable, "-m", "storage.migrate")

    step("Chạy API + frontend (Ctrl+C để dừng)")
    # Có chứng chỉ (python -m security.tls) -> frontend chạy https, API chỉ nghe trong máy (T-27)
    https = (ROOT / "data" / "certs" / "cert.pem").exists()
    scheme, api_host = ("https", "127.0.0.1") if https else ("http", "0.0.0.0")
    procs = [
        subprocess.Popen([sys.executable, "-m", "uvicorn", "api.main:app", "--reload",
                          "--host", api_host, "--port", "8000"], cwd=ROOT),
        subprocess.Popen([NPM, "run", "dev"], cwd=FRONTEND),
    ]
    print(f"\n  Webapp   {scheme}://localhost:5500"
          "\n  API      http://localhost:8000/health"
          "\n  Adminer  http://localhost:8080\n", flush=True)
    try:
        for _ in range(60):  # mở trình duyệt ngay khi frontend lên
            if port_open(5500) or any(p.poll() is not None for p in procs):
                break
            time.sleep(0.5)
        if port_open(5500):
            webbrowser.open(f"{scheme}://localhost:5500")
        # Dừng cả cụm nếu 1 tiến trình chết (VD lỗi code API, cổng bị chiếm)
        while all(p.poll() is None for p in procs):
            time.sleep(1)
        print("\n[LỖI] API hoặc frontend đã dừng - xem log phía trên.", flush=True)
        crashed = True
    except KeyboardInterrupt:
        crashed = False
    finally:
        print("\nĐang dừng...", flush=True)
        for p in procs:
            if p.poll() is None:
                if IS_WINDOWS:  # npm.cmd sinh tiến trình con (node) - phải kill cả cây
                    subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
                else:
                    p.terminate()
        subprocess.run([*docker, "compose", "stop"], cwd=ROOT)
        print("Đã dừng.", flush=True)
    sys.exit(1 if crashed else 0)


if __name__ == "__main__":
    main()
