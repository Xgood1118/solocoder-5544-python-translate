#!/bin/bash
echo "============================================"
echo "  Local Translation Service - Startup"
echo "============================================"
echo ""

cd "$(dirname "$0")"

if [ ! -f "venv/bin/python" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment."
        exit 1
    fi
    echo "Virtual environment created."
    echo ""
    echo "Installing dependencies..."
    venv/bin/pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies."
        exit 1
    fi
    echo "Dependencies installed."
    echo ""
fi

echo "Starting translation service on port ${PORT:-8330}..."
echo ""
venv/bin/python app.py
