#!/usr/bin/env bash
# Fiverr SERP Analyzer — Linux / macOS launcher
#
# Usage:
#   ./run.sh                          # default: reads config.yaml keywords
#   ./run.sh --input keywords.csv
#   ./run.sh --input keywords.csv --top 20
#   ./run.sh --keyword "scrape ecommerce website"
#   ./run.sh --input keywords.csv --resume
#   ./run.sh --input keywords.csv --force
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── banner ────────────────────────────────────────────────────────────────
echo "============================================"
echo "  Fiverr SERP Analyzer"
echo "============================================"
echo ""

# ── Python check ──────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 is not installed or not in PATH."
    echo "Please install Python 3.9+ from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
REQUIRED_MAJOR=3
REQUIRED_MINOR=9

IFS='.' read -r py_major py_minor <<< "$PYTHON_VERSION"
if [ "$py_major" -lt "$REQUIRED_MAJOR" ] || { [ "$py_major" -eq "$REQUIRED_MAJOR" ] && [ "$py_minor" -lt "$REQUIRED_MINOR" ]; }; then
    echo "ERROR: Python $PYTHON_VERSION detected, but $REQUIRED_MAJOR.$REQUIRED_MINOR+ is required."
    echo "Please install Python $REQUIRED_MAJOR.$REQUIRED_MINOR+ from https://www.python.org/downloads/"
    exit 1
fi

echo "Python $PYTHON_VERSION detected."

# ── virtual environment ───────────────────────────────────────────────────
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# ── dependencies ──────────────────────────────────────────────────────────
echo "Checking dependencies..."
if ! python3 -c "import selenium, yaml, openpyxl" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r "$SCRIPT_DIR/requirements.txt"
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install dependencies."
        exit 1
    fi
fi

# ── run ───────────────────────────────────────────────────────────────────
echo ""
echo "Starting Fiverr SERP Analyzer..."
echo "The browser will open in a visible window."
echo "You can press Ctrl+C at any time to stop and save progress."
echo ""

python3 "$SCRIPT_DIR/main.py" "$@"

echo ""
echo "============================================"
echo "  Run complete. Reports saved to this folder."
echo "============================================"
