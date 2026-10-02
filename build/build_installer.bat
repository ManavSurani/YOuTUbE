@echo off
setlocal

echo ========================================================
echo 1. Building frozen application with PyInstaller...
echo ========================================================
call build\build_exe.bat
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Application build failed.
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo 2. Code signing check (optional)...
echo ========================================================
set "SIGNTOOL_CMD="
where signtool.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 set "SIGNTOOL_CMD=signtool.exe"

if defined SIGNTOOL_CMD (
    if defined SIGN_CERT_FILE (
        echo Signing dist\YOuTUbE\YOuTUbE.exe...
        "%SIGNTOOL_CMD%" sign /f "%SIGN_CERT_FILE%" /p "%SIGN_CERT_PASS%" /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 "dist\YOuTUbE\YOuTUbE.exe"
    ) else (
        echo No certificate specified; skipping signing silently.
    )
) else (
    echo signtool not found; skipping signing silently.
)

echo.
echo ========================================================
echo 3. Compiling Inno Setup installer...
echo ========================================================
set "ISCC_PATH="
where iscc.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 set "ISCC_PATH=iscc.exe"

if defined ISCC_PATH goto ISCC_FOUND

if exist "C:\Users\Jay\AppData\Local\Programs\Antigravity IDE\resources\app\node_modules\innosetup\bin\ISCC.exe" (
    set "ISCC_PATH=C:\Users\Jay\AppData\Local\Programs\Antigravity IDE\resources\app\node_modules\innosetup\bin\ISCC.exe"
    goto ISCC_FOUND
)
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    goto ISCC_FOUND
)
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
    goto ISCC_FOUND
)

echo [ERROR] Inno Setup compiler (ISCC.exe) not found.
exit /b 1

:ISCC_FOUND
echo Using Inno Setup compiler: "%ISCC_PATH%"
"%ISCC_PATH%" installer\setup.iss
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Inno Setup compilation failed with code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

if defined SIGNTOOL_CMD (
    if defined SIGN_CERT_FILE (
        echo Signing Output\YOuTUbE_Setup.exe...
        "%SIGNTOOL_CMD%" sign /f "%SIGN_CERT_FILE%" /p "%SIGN_CERT_PASS%" /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 "Output\YOuTUbE_Setup.exe"
    )
)

echo.
echo ========================================================
echo 4. Installer SHA-256 Hash
echo ========================================================
if exist "Output\YOuTUbE_Setup.exe" (
    certutil -hashfile Output\YOuTUbE_Setup.exe SHA256
    echo.
    echo Successfully produced Output\YOuTUbE_Setup.exe
) else (
    echo [ERROR] Output\YOuTUbE_Setup.exe was not created.
    exit /b 1
)
endlocal
