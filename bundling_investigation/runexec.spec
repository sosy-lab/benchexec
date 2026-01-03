# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['../benchexec/runexecutor.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'benchexec',
        'benchexec.runexecutor',
        'benchexec.baseexecutor',
        'benchexec.containerexecutor',
        'benchexec.container',
        'benchexec.libc',
        'benchexec.util',
        'benchexec.cgroups',
        'benchexec.cgroupsv1',
        'benchexec.cgroupsv2',
        'benchexec.systeminfo',
        'benchexec.seccomp',
        'yaml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'benchexec.tablegenerator',
        'benchexec.benchexec',
        'benchexec.tools',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='runexec',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
