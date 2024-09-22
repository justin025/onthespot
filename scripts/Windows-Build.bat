@echo off
echo ========= OnTheSpot Windows Build Script ===========

echo => Cleaning up previous builds...
if exist build\ (
    rmdir build /s /q
)
if exist __pycache__\ (
    rmdir __pycache__ /s /q
)
if exist venvwin\ (
    rmdir venvwin /s /q
)
if exist dist\onthespot_win.exe (
    del /F /Q dist\onthespot_win.exe
)
if exist dist\onthespot_win_ffm.exe (
    del /F /Q dist\onthespot_win_ffm.exe
)

echo => Creating virtual environment...
python -m venv venvwin

echo => Activating virtual environment...
call venvwin\Scripts\activate.bat

echo => Upgrading pip and installing build tools...
pip install --upgrade pip
pip install wheel
pip install pyinstaller

echo => Installing project dependencies...
pip install winsdk
pip install -r requirements.txt

echo => Checking for embedded FFmpeg binaries...
if exist ffbin_win\ffmpeg.exe (
    echo => Found 'ffbin_win' directory and FFmpeg binary. Building with embedded FFmpeg...
    set BUILD_NAME=onthespot_win_ffm
    set ADD_BINARIES=--add-binary="ffbin_win\*.exe;onthespot/bin/ffmpeg"
) else (
    echo => No embedded FFmpeg found. Building to use system FFmpeg...
    set BUILD_NAME=onthespot_win
    set ADD_BINARIES=
)

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
    --paths="src/onthespot" ^
    --name="%BUILD_NAME%" ^
    --icon="src/onthespot/resources/icons/onthespot.png" ^
    src\portable.py

echo => Cleaning up temporary files...
if exist %BUILD_NAME%.spec (
    del /F /Q %BUILD_NAME%.spec
)
if exist build\ (
    rmdir build /s /q
)
if exist __pycache__\ (
    rmdir __pycache__ /s /q
)
if exist venvwin\ (
    rmdir venvwin /s /q
)

echo => Build completed successfully!
