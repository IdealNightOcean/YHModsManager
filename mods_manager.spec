# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import platform

block_cipher = None

PROJECT_ROOT = os.path.dirname(os.path.abspath(SPEC))

def get_icon_path():
    """根据平台返回图标路径"""
    system = platform.system()
    if system == 'Windows':
        icon_path = os.path.join(PROJECT_ROOT, 'icons', 'app_icon.ico')
        if os.path.exists(icon_path):
            print(f"使用图标文件: {icon_path}")
            return icon_path
        else:
            print(f"警告: 图标文件不存在: {icon_path}")
            return None
    elif system == 'Darwin':
        icon_path = os.path.join(PROJECT_ROOT, 'icons', 'app_icon.icns')
        if os.path.exists(icon_path):
            return icon_path
        return None
    else:
        return None

a = Analysis(
    ['main.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        (os.path.join(PROJECT_ROOT, 'config'), 'config'),
        (os.path.join(PROJECT_ROOT, 'icons'), 'icons'),
    ],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'watchdog',
        'watchdog.observers',
        'watchdog.events',
        'xml',
        'xml.etree',
        'xml.etree.ElementTree',
        'xml.dom',
        'xml.sax',
        'xml.parsers',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'plugins',
        'plugins_dev',
        'scripts',
        'docs',
        'cache',
        '.git',
        '.gitignore',
        '__pycache__',
        '*.pyc',
        '*.spec',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='YHModsManager',
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
    icon=get_icon_path(),
)
