@echo off

echo ========= OnTheSpot Windows Build Script =========

REM Check the current folder and change directory if necessary
set FOLDER_NAME=%cd%
for %%F in ("%cd%") do set FOLDER_NAME=%%~nxF

if /i "%FOLDER_NAME%"=="scripts" (
    echo You are in the scripts folder. Changing to the parent directory...
    cd ..
) else if /i not "%FOLDER_NAME%"=="onthespot" (
    echo Make sure that you are inside the project folder. Current folder is: %FOLDER_NAME%
    exit /b 1
)

REM Clean up previous builds
echo =^> Cleaning up previous builds...
del /F /Q /A dist\onthespot_win.exe 2>nul
del /F /Q /A dist\onthespot_win_ffm.exe 2>nul

REM Create virtual environment
echo =^> Creating virtual environment...
python -m venv venvwin

REM Activate virtual environment
echo =^> Activating virtual environment...
call venvwin\Scripts\activate.bat

REM Install dependencies
echo =^> Installing dependencies via pip...
python -m pip install --upgrade pip wheel winsdk pyinstaller
pip install -r requirements.txt

REM Check for ffmpeg binary and build
if exist ffbin_win\ffmpeg.exe (
    echo =^> Found ffmpeg binary, including it in the build...
    pyinstaller --onefile --noconsole --noconfirm ^
        --hidden-import="zeroconf._utils.ipaddress" ^
        --hidden-import="zeroconf._handlers.answers" ^
        --add-data="src/onthespot/resources/translations/*.qm;onthespot/resources/translations" ^
        --add-data="src/onthespot/resources/themes/*.qss;onthespot/resources/themes" ^
        --add-data="src/onthespot/gui/qtui/*.ui;onthespot/gui/qtui" ^
        --add-data="src/onthespot/resources/icons/*.png;onthespot/resources/icons" ^
        --add-binary="ffbin_win/*.exe;onthespot/bin/ffmpeg" ^
        --paths="src/onthespot" ^
        --name="onthespot_win_ffm" ^
        --icon="src/onthespot/resources/icons/onthespot.png" ^
        src\portable.py
) else (
    echo =^> FFmpeg binary not found, building without it...
    pyinstaller --onefile --noconsole --noconfirm ^
        --hidden-import="zeroconf._utils.ipaddress" ^
        --hidden-import="zeroconf._handlers.answers" ^
        --add-data="src/onthespot/resources/translations/*.qm;onthespot/resources/translations" ^
        --add-data="src/onthespot/resources/themes/*.qss;onthespot/resources/themes" ^
        --add-data="src/onthespot/gui/qtui/*.ui;onthespot/gui/qtui" ^
        --add-data="src/onthespot/resources/icons/*.png;onthespot/resources/icons" ^
        --paths="src/onthespot" ^
        --name="onthespot_win" ^
        --icon="src/onthespot/resources/icons/onthespot.png" ^
        src\portable.py
)

REM Clean up unnecessary files
echo =^> Cleaning up temporary files...
del /F /Q onthespot_win.spec 2>nul
del /F /Q onthespot_win_ffm.spec 2>nul
rmdir /s /q build 2>nul
rmdir /s /q __pycache__ 2>nul
rmdir /s /q venvwin 2>nul

echo =^> Done!
