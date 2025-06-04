# to build a stand-alone exe, run the command: pyinstaller length_of_day_app_qt.spec
# can try the pyinstaller --clean <file_name.spec> option

# -*- mode: python ; coding: utf-8 -*-

import os

a = Analysis(
    ['length_of_day_app_qt.py'],
    pathex=['.'],
    binaries=[],
    #datas=[('bw.ico', '.')],
    datas=[ 
        ('bw.ico', '.'),
        (r'C:\Users\barry\OneDrive - K-Space Associates, Inc\Documents\Python\length_of_day_src\.venv\Lib\site-packages\PySide6\plugins\platforms', 'PySide6/plugins/platforms'),
    ],
    hiddenimports=['PySide6.QtWidgets', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtPlatformSupport'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    # Set QT_PLUGIN_PATH environment variable for the build process
    env={
        'QT_PLUGIN_PATH': r'C:\Users\barry\OneDrive - K-Space Associates, Inc\Documents\Python\length_of_day_src\.venv\Lib\site-packages\PySide6\plugins'
    }
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='length_of_day_app_qt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['bw.ico'],
    onefile=True,  # This makes it a single executable
)
