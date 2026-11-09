import hashlib
from pathlib import Path

import PyInstaller.__main__ as pyi

EXE_NAME = "SmoothScroll-Patcher"
DIST_DIR = Path("dist")


def write_checksum() -> None:
    exe = DIST_DIR / f"{EXE_NAME}.exe"
    digest = hashlib.sha256(exe.read_bytes()).hexdigest()
    checksum = exe.with_name(f"{exe.name}.sha256")
    checksum.write_text(f"{digest} *{exe.name}\n", encoding="ascii")
    print(f"SHA-256: {digest}")


def main() -> None:
    pyi.run(
        pyi_args=[
            "main.py",
            f"--name={EXE_NAME}",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--windowed",
            "--noconsole",
            "--icon=src/assets/icon.ico",
            "--add-data=src/assets;assets",
            "--add-data=src/payload;payload",
            "--collect-all=customtkinter",
            "--hidden-import=psutil",
            "--hidden-import=pyuac",
            "--exclude-module=PyInstaller",
        ]
    )
    write_checksum()


if __name__ == "__main__":
    main()
