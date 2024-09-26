@echo off

REM =======================================
REM OnTheSpot Windows Build Script
REM =======================================
REM This script automates the build process for the OnTheSpot Windows application.
REM It creates a virtual environment, installs dependencies, and uses PyInstaller
REM to build the application, optionally including the FFmpeg binary.

REM Variables
set "VENV_DIR=venvwin"                                  REM Virtual environment directory
set "DIST_DIR=dist"                                     REM Distribution directory
set "BUILD_DIR=build"                                   REM Build directory
set "APP_NAME_NOFFM=onthespot_win"                      REM Application name without FFmpeg
set "APP_NAME_FFM=onthespot_win_ffm"                    REM Application name with FFmpeg
set "FFMPEG_DIR=ffbin_win"                              REM Directory containing FFmpeg binary
set "FFMPEG_BINARY=%FFMPEG_DIR%\ffmpeg.exe"             REM Path to FFmpeg binary
set "SOURCE_SCRIPT=src\portable.py"                     REM Main Python script to build
set "ICON_PATH=src\onthespot\resources\icons\onthespot.png"   REM Path to application icon
set "ADDITIONAL_PATHS=src\onthespot"                    REM Additional paths to include in PyInstaller

REM =======================================
REM Main Script Execution
REM =======================================

echo ========= OnTheSpot Windows Build Script =========

REM 1. Cleaning up previous builds
echo.
echo [1/9] Cleaning up previous builds...
if exist "%BUILD_DIR%" (
    rmdir /s /q "%BUILD_DIR%"
)
if exist "__pycache__" (
    rmdir /s /q "__pycache__"
)
if exist "%VENV_DIR%" (
    rmdir /s /q "%VENV_DIR%"
)
if exist "%DIST_DIR%\%APP_NAME_NOFFM%.exe" (
    del /F /Q "%DIST_DIR%\%APP_NAME_NOFFM%.exe"
)
if exist "%DIST_DIR%\%APP_NAME_FFM%.exe" (
    del /F /Q "%DIST_DIR%\%APP_NAME_FFM%.exe"
)
REM Clean up any previous .spec files
if exist "%APP_NAME_NOFFM%.spec" (
    del /F /Q "%APP_NAME_NOFFM%.spec"
)
if exist "%APP_NAME_FFM%.spec" (
    del /F /Q "%APP_NAME_FFM%.spec"
)
echo Cleanup completed.

REM 2. Creating virtual environment
echo.
echo [2/9] Creating virtual environment...
python -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo Error: Failed to create virtual environment.
    pause
    exit /b 1
)
echo Virtual environment created successfully.

REM 3. Activating virtual environment
echo.
echo [3/9] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo Error: Failed to activate virtual environment.
    pause
    exit /b 1
)
echo Virtual environment activated.

REM 4. Upgrading pip and installing build tools
echo.
echo [4/9] Upgrading pip and installing build tools...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo Error: Failed to upgrade pip.
    pause
    exit /b 1
)
python -m pip install --upgrade wheel
if errorlevel 1 (
    echo Error: Failed to install wheel.
    pause
    exit /b 1
)
python -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo Error: Failed to install PyInstaller.
    pause
    exit /b 1
)
echo Build tools installed successfully.

REM 5. Installing project dependencies
echo.
echo [5/9] Installing project dependencies...

REM Check if requirements.txt exists
if exist "requirements.txt" (
    echo Found requirements.txt. Installing dependencies...
    python -m pip install --upgrade -r requirements.txt
    if errorlevel 1 (
        echo Error: Failed to install project requirements.
        pause
        exit /b 1
    )
    echo Project dependencies installed successfully.
) else (
    echo WARNING: requirements.txt not found. Skipping installation of project dependencies.
)

REM 6. Checking for embedded FFmpeg binaries
echo.
echo [6/9] Checking for embedded FFmpeg binaries...
if exist "%FFMPEG_BINARY%" (
    echo Found FFmpeg binary in '%FFMPEG_DIR%'. Including FFmpeg in the build.
    set "BUILD_NAME=%APP_NAME_FFM%"
    set "ADD_BINARIES=--add-binary=%FFMPEG_DIR%\*.exe;onthespot/bin/ffmpeg"
) else (
    echo FFmpeg binary not found. Building without including FFmpeg.
    set "BUILD_NAME=%APP_NAME_NOFFM%"
    set "ADD_BINARIES="
)

REM 7. Running PyInstaller to build the application
echo.
echo [7/9] Running PyInstaller to build the application...

set "HIDDEN_IMPORTS=--hidden-import=zeroconf._utils.ipaddress --hidden-import=zeroconf._handlers.answers"

set "DATA_FILES=--add-data=src/onthespot/resources/translations/*.qm;onthespot/resources/translations --add-data=src/onthespot/resources/themes/*.qss;onthespot/resources/themes --add-data=src/onthespot/gui/qtui/*.ui;onthespot/gui/qtui --add-data=src/onthespot/resources/icons/*.png;onthespot/resources/icons"

pyinstaller ^
    --onefile ^
    --noconsole ^
    --noconfirm ^
    %HIDDEN_IMPORTS% ^
    %DATA_FILES% ^
    %ADD_BINARIES% ^
    --paths="%ADDITIONAL_PATHS%" ^
    --name="%BUILD_NAME%" ^
    --icon="%ICON_PATH%" ^
    "%SOURCE_SCRIPT%"

if errorlevel 1 (
    echo Error: PyInstaller build failed.
    pause
    exit /b 1
)
echo PyInstaller build completed successfully.

REM 8. Deactivating virtual environment
echo.
echo [8/9] Deactivating virtual environment...
call "%VENV_DIR%\Scripts\deactivate.bat"
echo Virtual environment deactivated.

REM 9. Build completed
echo.
echo [9/9] Build completed successfully!
pause

REM End of script
