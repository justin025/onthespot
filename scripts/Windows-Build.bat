@echo off

REM =======================================
REM OnTheSpot Windows Build Script
REM =======================================
REM This script automates the build process for the OnTheSpot Windows application.
REM It creates a virtual environment, installs dependencies, and uses PyInstaller
REM to build the application, optionally including the FFmpeg binary.

REM Variables
set VENV_DIR=venvwin                                  REM Virtual environment directory
set DIST_DIR=dist                                     REM Distribution directory
set BUILD_DIR=build                                   REM Build directory
set APP_NAME_NOFFM=onthespot_win                      REM Application name without FFmpeg
set APP_NAME_FFM=onthespot_win_ffm                    REM Application name with FFmpeg
set FFMPEG_DIR=ffbin_win                              REM Directory containing FFmpeg binary
set FFMPEG_BINARY=%FFMPEG_DIR%\ffmpeg.exe             REM Path to FFmpeg binary
set SOURCE_SCRIPT=src\portable.py                     REM Main Python script to build
set ICON_PATH=src\onthespot\resources\icons\onthespot.png   REM Path to application icon
set ADDITIONAL_PATHS=src\onthespot                    REM Additional paths to include in PyInstaller

REM =======================================
REM Main Script Execution 
REM =======================================

echo ========= OnTheSpot Windows Build Script =========

REM 1. Cleaning up previous builds
echo => Cleaning up previous builds...
if exist %BUILD_DIR%\ (
    rmdir /s /q %BUILD_DIR%
)
if exist __pycache__\ (
    rmdir /s /q __pycache__
)
if exist %VENV_DIR%\ (
    rmdir /s /q %VENV_DIR%
)
if exist %DIST_DIR%\%APP_NAME_NOFFM%.exe (
    del /F /Q %DIST_DIR%\%APP_NAME_NOFFM%.exe
)
if exist %DIST_DIR%\%APP_NAME_FFM%.exe (
    del /F /Q %DIST_DIR%\%APP_NAME_FFM%.exe
)
REM Clean up any previous .spec files
if exist %APP_NAME_NOFFM%.spec (
    del /F /Q %APP_NAME_NOFFM%.spec
)
if exist %APP_NAME_FFM%.spec (
    del /F /Q %APP_NAME_FFM%.spec
)

REM 2: Creating virtual environment
echo => Creating virtual environment...
python -m venv %VENV_DIR%
if errorlevel 1 (
    echo Error: Failed to create virtual environment.
    exit /b 1
)

REM 3. Activating virtual environment
echo => Activating virtual environment...
call %VENV_DIR%\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Failed to activate virtual environment.
    exit /b 1
)

REM 4. Upgrading pip and installing build tools
echo => Upgrading pip and installing build tools...
pip install --upgrade pip
if errorlevel 1 (
    echo Error: Failed to upgrade pip.
    exit /b 1
)
pip install wheel
if errorlevel 1 (
    echo Error: Failed to install wheel.
    exit /b 1
)
pip install pyinstaller
if errorlevel 1 (
    echo Error: Failed to install PyInstaller.
    exit /b 1
)

REM 5. Installing project dependencies
echo => Installing project dependencies...
pip install winsdk
if errorlevel 1 (
    echo Error: Failed to install winsdk.
    exit /b 1
)
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install project requirements.
    exit /b 1
)

REM 6. Checking for embedded FFmpeg binaries
echo => Checking for embedded FFmpeg binaries...
if exist "%FFMPEG_BINARY%" (
    echo => Found FFmpeg binary in '%FFMPEG_DIR%'. Including FFmpeg in the build.
    set BUILD_NAME=%APP_NAME_FFM%
    set ADD_BINARIES=--add-binary="%FFMPEG_DIR%\*.exe;onthespot/bin/ffmpeg"
) else (
    echo => FFmpeg binary not found. Building without including FFmpeg.
    set BUILD_NAME=%APP_NAME_NOFFM%
    set ADD_BINARIES=
)

REM 7. Running PyInstaller to build the application
echo => Running PyInstaller...
pyinstaller ^
    --onefile ^
    --noconsole ^
    --noconfirm ^
    --hidden-import="zeroconf._utils.ipaddress" ^
    --hidden-import="zeroconf._handlers.answers" ^
    --add-data="src/onthespot/resources/translations/*.qm;onthespot/resources/translations" ^
    --add-data="src/onthespot/resources/themes/*.qss;onthespot/resources/themes" ^
    --add-data="src/onthespot/gui/qtui/*.ui;onthespot/gui/qtui" ^
    --add-data="src/onthespot/resources/icons/*.png;onthespot/resources/icons" ^
    %ADD_BINARIES% ^
    --paths="%ADDITIONAL_PATHS%" ^
    --name="%BUILD_NAME%" ^
    --icon="%ICON_PATH%" ^
    %SOURCE_SCRIPT%
if errorlevel 1 (
    echo Error: PyInstaller build failed.
    exit /b 1
)

REM 8. Deactivating virtual environment
echo => Deactivating virtual environment...
call deactivate.bat

REM 9. Cleaning up temporary files
echo => Cleaning up temporary files...
if exist %BUILD_NAME%.spec (
    del /F /Q %BUILD_NAME%.spec
)
if exist %BUILD_DIR%\ (
    rmdir /s /q %BUILD_DIR%
)
if exist __pycache__\ (
    rmdir /s /q __pycache__
)
REM Optionally remove the virtual environment
if exist %VENV_DIR%\ (
    rmdir /s /q %VENV_DIR%
)

REM 10. Build completed
echo => Build completed successfully!

REM End of script
