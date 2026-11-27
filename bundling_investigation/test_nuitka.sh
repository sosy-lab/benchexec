#!/bin/bash
# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2025 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# Test Nuitka bundling of runexec


set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$SCRIPT_DIR/output"
LOGS_DIR="$SCRIPT_DIR/logs"

echo "=== Testing Nuitka for runexec bundling ==="
echo ""

# Create directories
mkdir -p "$OUTPUT_DIR" "$LOGS_DIR"

# Install Nuitka if needed
if ! python3 -c "import nuitka" 2>/dev/null; then
    echo "Installing Nuitka..."
    pip install nuitka ordered-set
fi

echo "Building with Nuitka (this may take 10-20 minutes)..."
cd "$PROJECT_ROOT"

python3 -m nuitka \
    --onefile \
    --follow-imports \
    --include-package=benchexec \
    --include-module=yaml \
    --nofollow-import-to=benchexec.tablegenerator \
    --nofollow-import-to=benchexec.benchexec \
    --nofollow-import-to=benchexec.tools \
    --output-filename=runexec-nuitka \
    --output-dir="$OUTPUT_DIR" \
    benchexec/runexecutor.py \
    > "$LOGS_DIR/nuitka_build.log" 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Build successful"
    
    # Nuitka may create .bin file
    if [ -f "$OUTPUT_DIR/runexec-nuitka.bin" ]; then
        mv "$OUTPUT_DIR/runexec-nuitka.bin" "$OUTPUT_DIR/runexec-nuitka"
    fi
    
    if [ -f "$OUTPUT_DIR/runexec-nuitka" ]; then
        chmod +x "$OUTPUT_DIR/runexec-nuitka"
        echo ""
        echo "Binary created:"
        ls -lh "$OUTPUT_DIR/runexec-nuitka"
        echo ""
        
        # Basic tests
        echo "Running basic tests..."
        
        echo "Test 1: --version"
        if "$OUTPUT_DIR/runexec-nuitka" --version > "$LOGS_DIR/nuitka_test_version.log" 2>&1; then
            echo "✓ Version check passed"
        else
            echo "✗ Version check failed"
        fi
        
        echo "Test 2: --help"
        if "$OUTPUT_DIR/runexec-nuitka" --help > "$LOGS_DIR/nuitka_test_help.log" 2>&1; then
            echo "✓ Help passed"
        else
            echo "✗ Help failed"
        fi
        
        echo "Test 3: Simple command"
        if "$OUTPUT_DIR/runexec-nuitka" echo "Hello from Nuitka" > "$LOGS_DIR/nuitka_test_simple.log" 2>&1; then
            echo "✓ Simple command passed"
        else
            echo "✗ Simple command failed"
        fi
        
        echo ""
        echo "Build complete! Binary: $OUTPUT_DIR/runexec-nuitka"
    else
        echo "✗ Binary not found after build"
        exit 1
    fi
else
    echo "✗ Build failed - check logs/nuitka_build.log"
    exit 1
fi
