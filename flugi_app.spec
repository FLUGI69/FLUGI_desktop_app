# -*- mode: python ; coding: utf-8 -*-
import os
import glob

def generate_datas(base_dir):

    datas = []

    for root, dirs, files in os.walk(base_dir):
        
        rel_root = os.path.relpath(root, base_dir)

        target_dir = os.path.join(base_dir, rel_root) if rel_root != '.' else base_dir
        
        if files:
        
            datas.append((os.path.join(root, '*'), target_dir))
            
    return datas

datas = generate_datas('gui')

a = Analysis(
    ['gui\\__main__.py'],
    pathex=['gui'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'aiomysql',
        'utils.dc.admin.current_tenant',
        'utils.dc.admin.period_info',
        'cffi',
        'pycparser',
        'weasyprint',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='example_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['example_path'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='example_app',
)
