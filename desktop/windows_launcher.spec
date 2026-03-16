# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path.cwd()
seed_dir = project_root / 'desktop' / 'seed'

datas = [
    (str(project_root / 'desktop' / 'windows_launcher.py'), 'desktop'),
    (str(seed_dir / 'db.sqlite3'), 'seed'),
    (str(seed_dir / 'media'), 'seed/media'),
    (str(project_root / 'static'), 'static'),
]

hiddenimports = [
    'webvtes.settings_desktop',
]


a = Analysis(
    ['desktop/windows_launcher.py'],
    pathex=[str(project_root)],
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
    a.binaries,
    a.datas,
    [],
    name='WebVTESLauncher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
