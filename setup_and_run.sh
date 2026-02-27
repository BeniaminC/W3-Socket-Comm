#!/bin/bash

# Exit script immediately on any error
set -e

echo "==========================================="
echo " Setting up WC3 Client Environment"
echo "==========================================="

# Define paths
LOCAL_INDEX="index.js"
# Note: In Git Bash, Windows paths can be used directly if enclosed in quotes.
WEBUI_DIR="C:/Program Files (x86)/Warcraft III/_retail_/webui"
TARGET_INDEX="$WEBUI_DIR/index.js"

# 1. Copy index.js
if [ -f "$LOCAL_INDEX" ]; then
    echo "[1/4] Copying index.js to Game Directory..."
    # Create the directory if it doesn't exist
    mkdir -p "$WEBUI_DIR"
    cp "$LOCAL_INDEX" "$TARGET_INDEX"
    echo "  -> Copied successfully."
else
    echo "[!] Warning: Local index.js not found. Skipping copy."
fi

# 2. Create Python virtual environment
echo "[2/4] Creating Python Virtual Environment (venv)..."
if [ ! -d ".venv" ]; then
    python -m venv .venv
fi

# Activate the venv (Windows specific path inside Bash)
echo "  -> Activating venv..."
source .venv/Scripts/activate

# 3. Pip Install exactly the specified versions
echo "[3/4] Installing dependencies..."
python -m pip install --upgrade pip
pip install \
    annotated-types==0.7.0 \
    keyboard==0.13.5 \
    pydantic==2.12.5 \
    pydantic_core==2.41.5 \
    pyperclip==1.11.0 \
    typing-inspection==0.4.2 \
    typing_extensions==4.15.0 \
    websockets==16.0 \
    pyinstaller

# 4. Run the Python files
echo "[4/4] Building exe..."
cd src
pyinstaller --noconfirm --onedir --windowed --add-data "index.js;." copy_battlenet_tags_script.py

