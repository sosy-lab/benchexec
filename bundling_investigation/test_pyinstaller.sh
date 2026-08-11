#!/bin/bash
# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2025 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# Test PyInstaller bundling of runexec


set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$SCRIPT_DIR/output"
LOGS_DIR="$SCRIPT_DIR/logs"

echo "=== Testing PyInstaller for runexec bundling ==="
echo ""

# Activate virtual environment if it exists
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Create directories
mkdir -p "$OUTPUT_DIR" "$LOGS_DIR"

# Check if PyInstaller is installed
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

# Create PyInstaller spec file
cat > "$SCRIPT_DIR/runexec.spec" << 'EOF'
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
EOF

echo "Building with PyInstaller..."
cd "$SCRIPT_DIR"
pyinstaller runexec.spec \
    --distpath "$OUTPUT_DIR" \
    --workpath "$SCRIPT_DIR/build" \
    --clean \
    > "$LOGS_DIR/pyinstaller_build.log" 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Build successful"
    
    # Show binary info
    if [ -f "$OUTPUT_DIR/runexec" ]; then
        echo ""
        echo "Binary created:"
        ls -lh "$OUTPUT_DIR/runexec"
        echo ""
        
        # Basic tests
        echo "Running basic tests..."
        
        echo "Test 1: --version"
        if "$OUTPUT_DIR/runexec" --version > "$LOGS_DIR/test_version.log" 2>&1; then
            echo "✓ Version check passed"
        else
            echo "✗ Version check failed (see logs/test_version.log)"
        fi
        
        echo "Test 2: --help"
        if "$OUTPUT_DIR/runexec" --help > "$LOGS_DIR/test_help.log" 2>&1; then
            echo "✓ Help passed"
        else
            echo "✗ Help failed (see logs/test_help.log)"
        fi
        
        echo "Test 3: Simple command"
        if "$OUTPUT_DIR/runexec" echo "Hello from bundled runexec" > "$LOGS_DIR/test_simple.log" 2>&1; then
            echo "✓ Simple command passed"
        else
            echo "✗ Simple command failed (see logs/test_simple.log)"
        fi
        
        echo "Test 4: Container mode"
        if "$OUTPUT_DIR/runexec" --container echo "Container test" > "$LOGS_DIR/test_container.log" 2>&1; then
            echo "✓ Container mode passed"
        else
            echo "✗ Container mode failed (see logs/test_container.log)"
        fi
        
        echo ""
        echo "Build complete! Binary: $OUTPUT_DIR/runexec"
        echo "Logs in: $LOGS_DIR/"
    else
        echo "✗ Binary not found after build"
        exit 1
    fi
else
    echo "✗ Build failed - check logs/pyinstaller_build.log"
    exit 1
fi
