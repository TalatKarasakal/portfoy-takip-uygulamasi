# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PROJECT_ROOT = Path(SPECPATH)
MACOS_ICON = PROJECT_ROOT / "app/resources/app_icon.icns"
WINDOWS_ICON = PROJECT_ROOT / "app/resources/app_icon.ico"
MACOS_BUNDLE_NAME = "Portföy Takip.app"
MACOS_BUNDLE_IDENTIFIER = "com.talat.portfoytakip"

datas = [
    (str(PROJECT_ROOT / "app/resources"), "app/resources"),
    (str(PROJECT_ROOT / "app/database/migrations"), "app/database/migrations"),
]
datas += collect_data_files("qtawesome")

platform_keyring_backend = {
    "darwin": "keyring.backends.macOS",
    "win32": "keyring.backends.Windows",
}.get(sys.platform, "keyring.backends.SecretService")

hiddenimports = collect_submodules("app") + [
    "keyring.backends.chainer",
    platform_keyring_backend,
    "sqlalchemy.dialects.sqlite",
]

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PortfolioTracker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(WINDOWS_ICON) if sys.platform == "win32" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="PortfolioTracker",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=MACOS_BUNDLE_NAME,
        icon=str(MACOS_ICON),
        bundle_identifier=MACOS_BUNDLE_IDENTIFIER,
        version="1.0.0",
    )
