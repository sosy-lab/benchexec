#!/bin/bash
# Production build script for bundled runexec
# Creates a standalone executable using PyInstaller

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Building Bundled runexec with PyInstaller ==="
echo ""

# Check if we're in the project root
if [ ! -f "$PROJECT_ROOT/benchexec/runexecutor.py" ]; then
    echo "Error: Must be run from BenchExec repository"
    exit 1
fi

# Activate virtual environment if it exists
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Install PyInstaller if needed
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

# Create output directory
OUTPUT_DIR="$SCRIPT_DIR/dist"
mkdir -p "$OUTPUT_DIR"

echo "Building runexec bundle..."
cd "$SCRIPT_DIR"

# Build with PyInstaller
pyinstaller runexec.spec \
    --distpath "$OUTPUT_DIR" \
    --workpath "$SCRIPT_DIR/build" \
    --clean

if [ -f "$OUTPUT_DIR/runexec" ]; then
    echo ""
    echo "✅ Build successful!"
    echo ""
    echo "Binary: $OUTPUT_DIR/runexec"
    ls -lh "$OUTPUT_DIR/runexec"
    echo ""
    echo "Dependencies:"
    ldd "$OUTPUT_DIR/runexec" | grep -v "=>" || ldd "$OUTPUT_DIR/runexec"
    echo ""
    echo "Test it:"
    echo "  $OUTPUT_DIR/runexec --version"
    echo "  $OUTPUT_DIR/runexec echo 'Hello World'"
else
    echo "❌ Build failed!"
    exit 1
fi
