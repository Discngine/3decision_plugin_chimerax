@echo off
REM ===============================================================================
REM ChimeraX 3decision Plugin Installer for Windows
REM Automatically detects ChimeraX installation and installs the plugin
REM ===============================================================================

setlocal enabledelayedexpansion

echo ========================================
echo ChimeraX 3decision Plugin Installer
echo Platform: Windows
echo ========================================

REM Function to find ChimeraX on Windows
set "CHIMERAX_PATH="
set "FOUND_CHIMERAX=false"

REM Check common installation paths
set "SEARCH_PATHS=%ProgramFiles%\ChimeraX*\bin\ChimeraX.exe"
set "SEARCH_PATHS=!SEARCH_PATHS! %ProgramFiles(x86)%\ChimeraX*\bin\ChimeraX.exe"
set "SEARCH_PATHS=!SEARCH_PATHS! %LOCALAPPDATA%\ChimeraX*\bin\ChimeraX.exe"
set "SEARCH_PATHS=!SEARCH_PATHS! %USERPROFILE%\AppData\Local\ChimeraX*\bin\ChimeraX.exe"

echo Searching for ChimeraX installation...

for %%P in (!SEARCH_PATHS!) do (
    for %%F in ("%%P") do (
        if exist "%%F" (
            set "CHIMERAX_PATH=%%F"
            set "FOUND_CHIMERAX=true"
            goto :found_chimerax
        )
    )
)

REM Also check registry for ChimeraX installation
for /f "tokens=2*" %%A in ('reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "ChimeraX" 2^>nul ^| findstr "InstallLocation"') do (
    if exist "%%B\bin\ChimeraX.exe" (
        set "CHIMERAX_PATH=%%B\bin\ChimeraX.exe"
        set "FOUND_CHIMERAX=true"
        goto :found_chimerax
    )
)

:found_chimerax
if "!FOUND_CHIMERAX!"=="false" (
    echo ❌ ChimeraX not found in standard locations.
    echo.
    echo Please install ChimeraX from: https://www.rbvi.ucsf.edu/chimerax/download.html
    echo Or set the path manually:
    echo   set CHIMERAX_PATH=C:\Path\To\ChimeraX\bin\ChimeraX.exe
    echo   %~nx0
    pause
    exit /b 1
)

echo ✅ Found ChimeraX: !CHIMERAX_PATH!

REM Get ChimeraX version
for /f "tokens=*" %%V in ('"!CHIMERAX_PATH!" --version 2^>nul ^| findstr ChimeraX') do (
    set "CHIMERAX_VERSION=%%V"
)
echo    Version: !CHIMERAX_VERSION!

echo.
echo Starting installation process...
echo Plugin directory: %CD%

REM Check if bundle_info.xml exists
if not exist "bundle_info.xml" (
    echo ❌ bundle_info.xml not found. Please run from the plugin directory.
    pause
    exit /b 1
)

echo.
echo Checking installation permissions...

REM Get ChimeraX site-packages directory
for /f "tokens=*" %%D in ('"!CHIMERAX_PATH!" -c "import site; print(site.getsitepackages()[0])" 2^>nul') do (
    set "SITE_PACKAGES_DIR=%%D"
)

if "!SITE_PACKAGES_DIR!"=="" (
    echo ❌ Could not determine ChimeraX site-packages directory
    pause
    exit /b 1
)

set "CHIMERAX_PACKAGES_DIR=!SITE_PACKAGES_DIR!\chimerax"
set "TARGET_DIR=!CHIMERAX_PACKAGES_DIR!\threedecision"

echo ChimeraX packages directory: !CHIMERAX_PACKAGES_DIR!

echo.
echo Cleaning up previous installations...

REM Remove existing installation
if exist "!TARGET_DIR!" (
    echo Removing existing installation: !TARGET_DIR!
    rmdir /s /q "!TARGET_DIR!" 2>nul
    if exist "!TARGET_DIR!" (
        echo ⚠️ Could not remove existing installation. You may need to run as Administrator.
    )
)

echo Building plugin...

REM Build the plugin
"!CHIMERAX_PATH!" --nogui --cmd "devel build %CD%; exit" >nul 2>&1
if !errorlevel! neq 0 (
    echo ❌ Plugin build failed
    pause
    exit /b 1
)

echo ✅ Plugin built successfully

echo.
echo Installing plugin...

REM Try standard installation first
echo Attempting standard ChimeraX installation...
"!CHIMERAX_PATH!" --nogui --cmd "devel install %CD%; exit" >nul 2>&1
if !errorlevel! equ 0 (
    echo ✅ Standard installation completed successfully
    goto :test_installation
)

echo Standard installation failed, trying manual installation...

REM Manual installation
if not exist "dist" (
    echo ❌ No dist directory found
    pause
    exit /b 1
)

REM Find wheel file
set "WHEEL_FILE="
for %%F in (dist\*.whl) do (
    set "WHEEL_FILE=%%F"
    goto :found_wheel
)

:found_wheel
if "!WHEEL_FILE!"=="" (
    echo ❌ No wheel file found in dist directory
    pause
    exit /b 1
)

echo Extracting wheel file: !WHEEL_FILE!

REM Create temporary directory
set "TEMP_DIR=%TEMP%\chimerax_plugin_install_%RANDOM%"
mkdir "!TEMP_DIR!"

REM Extract wheel (using PowerShell for ZIP extraction)
powershell -command "Expand-Archive -Path '!WHEEL_FILE!' -DestinationPath '!TEMP_DIR!' -Force"

REM Copy files to ChimeraX
echo Copying files to ChimeraX packages directory...
if exist "!TEMP_DIR!\chimerax\threedecision" (
    xcopy "!TEMP_DIR!\chimerax\threedecision" "!CHIMERAX_PACKAGES_DIR!\threedecision" /E /I /Y >nul
    if !errorlevel! equ 0 (
        echo ✅ Manual installation completed
    ) else (
        echo ❌ Failed to copy files. You may need to run as Administrator.
        goto :cleanup
    )
) else (
    echo ❌ Expected plugin files not found in wheel
    goto :cleanup
)

REM Cleanup temporary directory
:cleanup
if exist "!TEMP_DIR!" rmdir /s /q "!TEMP_DIR!"

:test_installation
echo.
echo Testing installation...

REM Test the installation
"!CHIMERAX_PATH!" --nogui --cmd "python 'import chimerax.threedecision; print(\"✅ Module import successful\")'; exit" 2>nul | findstr "Module import successful" >nul
if !errorlevel! equ 0 (
    echo ✅ Installation verified successfully
    set "INSTALL_SUCCESS=true"
) else (
    echo ❌ Installation verification failed
    echo The plugin was built but import test failed.
    set "INSTALL_SUCCESS=false"
)

echo.
echo ========================================
echo INSTALLATION COMPLETED!
echo ========================================
echo.

if "!INSTALL_SUCCESS!"=="true" (
    echo The threedecision plugin has been installed successfully.
    echo.
    echo To use the plugin:
    echo 1. Start ChimeraX
    echo 2. Use menu: Tools → Structure Analysis → Discngine 3decision
    echo 3. Or use command: threedecision ^(after registering - see README.md^)
) else (
    echo Installation encountered issues. You can try:
    echo 1. Running as Administrator
    echo 2. Check ChimeraX error messages
    echo 3. Verify ChimeraX version compatibility ^(1.8+^)
)

echo.
echo For configuration and usage instructions, see README.md
echo ========================================

pause
