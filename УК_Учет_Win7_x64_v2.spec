# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path
import customtkinter

SRC = Path(".").resolve()

# Find customtkinter directory to include its resources in the package
ctk_dir = Path(customtkinter.__file__).resolve().parent

# Auto-detect target architecture to include Windows 7 compatibility DLL
import struct
is_64bit = struct.calcsize("P") * 8 == 64
arch_folder = "x64" if is_64bit else "x86"
compat_dll = SRC / "compat" / arch_folder / "api-ms-win-core-path-l1-1-0.dll"

binaries_list = []
if compat_dll.exists():
    binaries_list.append((str(compat_dll), "."))

a = Analysis(
    ["run.py"],
    pathex=[str(SRC)],
    binaries=binaries_list,
    datas=[
        ("app/templates", "app/templates"),
        ("app/static",    "app/static"),
        ("app_icon.ico",  "."),
        ("app_icon.png",  "."),
        (str(ctk_dir), "customtkinter"),  # critical for customtkinter themes/assets
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "uvicorn._types",
        "fastapi",
        "starlette",
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.orm",
        "pystray._win32",
        "PIL",
        "PIL._tkinter_finder",
        "openpyxl",
        "docx",
        "anyio._backends._asyncio",
        "anyio._backends._trio",
        "email.mime.text",
        "email.mime.multipart",
        "darkdetect",
    ],
    excludes=["pytest", "hypothesis"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="УК_Учет_Win7_x64_v2" if is_64bit else "УК_Учет_Win7_x86_v2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,         # no terminal window — uses tkinter window instead
    windowed=True,
    icon="app_icon.ico",
)
