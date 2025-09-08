#!/bin/bash
set -e

echo "🐒 Starting Whispier Bot..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "🔧 Installing requirements..."
pip install -r requirements.txt

# Start the bot
echo "🚀 Launching Whispier Bot..."
python main.py