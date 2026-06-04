#!/usr/bin/env bash
# Small helper to create a venv and install required Python packages
set -euo pipefail

VENV=".venv"
if [ ! -d "$VENV" ]; then
  echo "Creating virtual environment in $VENV..."
  python3 -m venv "$VENV"
else
  echo "Virtual environment already exists at $VENV"
fi

# shellcheck source=/dev/null
source "$VENV/bin/activate"
python -m pip install --upgrade pip
pip install Pillow click pyinstaller

echo "Done. Activate with: source .venv/bin/activate"
echo "Then run: python gui.py"
