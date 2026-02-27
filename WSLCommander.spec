# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all qfluentwidgets resources (icons, QSS, i18n, etc.)
fluent_datas = collect_data_files('qfluentwidgets')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Application assets
        ('assets/distros/*.png', 'assets/distros'),
        ('assets/icon/*.png',    'assets/icon'),
        # qfluentwidgets bundled resources
        *fluent_datas,
    ],
    hiddenimports=[
        *collect_submodules('qfluentwidgets'),
        'PyQt6.QtSvg',
        'PyQt6.QtSvgWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WSLCommander',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                          # no console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon/icon.png',            # taskbar / exe icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WSLCommander',
)

