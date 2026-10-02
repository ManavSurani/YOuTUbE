@echo off
setlocal
echo Installing requirements...
pip install -r requirements.txt -r requirements-dev.txt
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install requirements.
    exit /b %ERRORLEVEL%
)

echo Building YOuTUbE with PyInstaller...
pyinstaller --noconsole --onedir --name YOuTUbE --icon assets\icon.ico --paths . --add-data "app\tools.json;app" --add-data "assets;assets" --noconfirm app\main.py
if %ERRORLEVEL% NEQ 0 (
    echo PyInstaller build failed with error %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

echo Build completed successfully: dist\YOuTUbE\YOuTUbE.exe
endlocal
