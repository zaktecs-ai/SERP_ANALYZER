#!/usr/bin/env bash
# Fiverr SERP Analyzer — Environment Setup (Linux / macOS)
#
# Creates an ISOLATED Python virtual environment just for this project.
# No conflicts with anything else on your computer.
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
# After setup, run: ./run.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  Fiverr SERP Analyzer - Environment Setup"
echo "============================================"
echo ""
echo "This script creates an ISOLATED Python environment"
echo "just for this project. No conflicts with anything else"
echo "on your computer."
echo ""

# ── Python check ──────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 is not installed or not in PATH."
    echo "Install Python 3.9+ from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "[OK] Python $PYTHON_VERSION detected"
echo ""

# ── Virtual Environment ───────────────────────────────────────────────────
VENV_DIR="$SCRIPT_DIR/.venv"

if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists at:"
    echo "  $VENV_DIR"
    echo ""
    read -rp "Recreate it from scratch? [y/N]: " RECREATE
    if [[ "${RECREATE,,}" =~ ^y(es)?$ ]]; then
        echo "Removing old environment..."
        rm -rf "$VENV_DIR"
    else
        echo "Keeping existing environment. Skipping creation."
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "[OK] Virtual environment created."
fi

# ── Activate & Install ────────────────────────────────────────────────────
source "$VENV_DIR/bin/activate"

echo ""
echo "Upgrading pip..."
pip install --upgrade pip --quiet

echo ""
echo "Installing project dependencies..."
pip install -r "$SCRIPT_DIR/requirements.txt"
echo "[OK] Dependencies installed."

echo ""
echo "============================================"
echo "  SETUP COMPLETE!"
echo "============================================"
echo ""
echo "Your isolated environment is ready at:"
echo "  $VENV_DIR"
echo ""
echo "To run the analyzer:"
echo "  ./run.sh"
echo ""
echo "Or manually:"
echo "  source .venv/bin/activate"
echo "  python main.py --keyword \"web scraping\""
echo ""
