#!/bin/bash

# Attendance Analyzer Setup Script
echo "🎉 Setting up Attendance Analyzer Web App..."

# Check if Python is installed
if ! command -v python &> /dev/null
then
    echo "❌ Python is not installed. Please install Python 3.7+ first."
    exit 1
fi

echo "✅ Python found"

# Create virtual environment
echo "📦 Creating virtual environment..."
python -m venv virtualenv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source virtualenv/Scripts/activate
else
    source virtualenv/bin/activate
fi

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🎊 Setup complete!"
echo "🌐 To start the application:"
echo "   1. Activate virtual environment:"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "      .\\virtualenv\\Scripts\\Activate.ps1"
else
    echo "      source virtualenv/bin/activate"
fi
echo "   2. Run the app:"
echo "      python app.py"
echo "   3. Open http://localhost:5000 in your browser"