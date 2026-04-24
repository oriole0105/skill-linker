# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

# Collect Textual and Rich (includes their internal CSS and data files)
textual_datas, textual_binaries, textual_hiddenimports = collect_all('textual')
rich_datas, rich_binaries, rich_hiddenimports = collect_all('rich')

# Collect the app's own .tcss file
skill_datas = collect_data_files('skill_linker', includes=['**/*.tcss'])

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=textual_binaries + rich_binaries,
    datas=skill_datas + textual_datas + rich_datas,
    hiddenimports=textual_hiddenimports + rich_hiddenimports + [
        'textual.widgets._data_table',
        'textual.widgets._input',
        'textual.widgets._label',
        'textual.widgets._button',
        'textual.widgets._footer',
        'textual.widgets._header',
        'textual.widgets._list_view',
        'textual.widgets._list_item',
        'textual.widgets._markdown',
        'textual.widgets._static',
        'skill_linker.config',
        'skill_linker.scanner',
        'skill_linker.linker',
        'skill_linker.tui.app',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='skill-linker',
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
