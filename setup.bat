@echo off
REM Attendance Analyzer Setup Script for Windows
echo 🎉 Setting up Attendance Analyzer Web App...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.7+ first.
    pause
    exit /b 1
)

echo ✅ Python found

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv virtualenv

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call virtualenv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo 🎊 Setup complete!
echo 🌐 To start the application:
echo    1. Activate virtual environment: .\virtualenv\Scripts\Activate.ps1
echo    2. Run the app: python app.py
echo    3. Open http://localhost:5000 in your browser
pause