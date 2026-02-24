#!/bin/bash
echo "======================================="
echo "PrismDB Studio - Linux/macOS Startup"
echo "======================================="

# OS check
OS="$(uname -s)"
echo "[INFO] Operating System detected as: $OS"

if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "[WARN] Python is not installed."
    if [ "$OS" = "Linux" ]; then
        if command -v apt-get &>/dev/null; then
            echo "[INFO] Attempting to install Python via apt..."
            sudo apt-get update
            sudo apt-get install -y python3 python3-venv python3-pip
            PYTHON_CMD="python3"
        elif command -v dnf &>/dev/null; then
            echo "[INFO] Attempting to install Python via dnf..."
            sudo dnf install -y python3
            PYTHON_CMD="python3"
        elif command -v yum &>/dev/null; then
            echo "[INFO] Attempting to install Python via yum..."
            sudo yum install -y python3
            PYTHON_CMD="python3"
        elif command -v pacman &>/dev/null; then
            echo "[INFO] Attempting to install Python via pacman..."
            sudo pacman -S python python-pip
            PYTHON_CMD="python"
        else
            echo "[ERROR] Unsupported package manager. Please install Python manually."
            exit 1
        fi
    elif [ "$OS" = "Darwin" ]; then
        if command -v brew &>/dev/null; then
            echo "[INFO] Attempting to install Python via Homebrew..."
            brew install python
            PYTHON_CMD="python3"
        else
            echo "[ERROR] Homebrew not found. Please install Python manually."
            exit 1
        fi
    else
        echo "[ERROR] Unsupported OS for automatic Python installation."
        exit 1
    fi
fi

echo "[INFO] Using Python command: $PYTHON_CMD"

# Check if venv exists
if [ ! -d "venv" ] || [ ! -f "venv/bin/activate" ]; then
    echo "[INFO] Virtual environment not found. Creating..."
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment."
        exit 1
    fi
    echo "[INFO] Virtual environment created successfully."
fi

# Activate the virtual environment
echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "[INFO] Ensuring pip is up to date..."
$PYTHON_CMD -m pip install --upgrade pip > /dev/null 2>&1
echo "[INFO] Installing/Verifying dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies."
    exit 1
fi

echo ""
echo "======================================="
echo "Starting PrismDB Studio..."
echo "======================================="
$PYTHON_CMD main.py
