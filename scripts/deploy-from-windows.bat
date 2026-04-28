@echo off
REM Phase 4: Automated ADB Deployment from Windows
REM This script deploys GURUJEE to Android device via ADB
REM Requires: Android SDK, ADB, connected device

setlocal enabledelayedexpansion

echo ╔════════════════════════════════════════════════════╗
echo ║  GURUJEE Android Deployment via ADB (Windows)     ║
echo ╚════════════════════════════════════════════════════╝
echo.

REM Find ADB executable
if exist "%ANDROID_HOME%\platform-tools\adb.exe" (
    set "ADB=%ANDROID_HOME%\platform-tools\adb.exe"
) else if exist "C:\Users\%USERNAME%\AppData\Local\Android\Sdk\platform-tools\adb.exe" (
    set "ADB=C:\Users\%USERNAME%\AppData\Local\Android\Sdk\platform-tools\adb.exe"
) else (
    echo ❌ ERROR: adb.exe not found
    echo Please set ANDROID_HOME or ensure Android SDK is installed
    exit /b 1
)

echo ✓ ADB found: %ADB%
echo.

REM Check device connection
echo Checking device connection...
for /f "tokens=1" %%A in ('"%ADB%" devices ^| find "device" ^| find /v "devices"') do (
    set "DEVICE=%%A"
    goto device_found
)

echo ❌ No Android device found
echo Please connect a device and enable ADB debugging
exit /b 1

:device_found
echo ✓ Device found: %DEVICE%
echo.

REM Set repository path
set "REPO_DIR=%~dp0\.."
echo 📁 Repository: %REPO_DIR%
echo.

REM Step 1: Push deployment script
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo STEP 1: Uploading automated setup script
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

"%ADB%" push "%REPO_DIR%\scripts\deploy-termux-automated.sh" "/sdcard/deploy-gurujee.sh"
if errorlevel 1 (
    echo ❌ Failed to push script
    exit /b 1
)
echo ✓ Script uploaded
echo.

REM Step 2: Instructions for user
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo STEP 2: Next Steps (On Your Android Device)
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 1. Open Termux on your device
echo.
echo 2. Copy and paste this command:
echo    bash /sdcard/deploy-gurujee.sh
echo.
echo 3. Wait for installation to complete (~2-3 minutes)
echo.
echo 4. Start the daemon:
echo    ~/GURUJEE/start.sh
echo.
echo 5. Verify it's working (in another Termux tab):
echo    curl http://localhost:7171/api/health
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM Optional: Show setup file details
echo 📝 Setup Details:
echo    Script: deploy-gurujee.sh
echo    Location: /sdcard/deploy-gurujee.sh
echo    Size: ~2KB
echo    Time to complete: 2-3 minutes
echo.

REM Check if we want to also try direct execution
set "AUTO_EXEC=N"
if "%1"=="--auto" (
    set "AUTO_EXEC=Y"
)

if "!AUTO_EXEC!"=="Y" (
    echo.
    echo ⚠️  Attempting automatic execution (this may not work due to Termux sandbox)...
    "%ADB%" shell "bash /sdcard/deploy-gurujee.sh"
)

echo.
echo ✓ Deployment script ready on device
echo ℹ️  Execute the script in Termux to complete setup
