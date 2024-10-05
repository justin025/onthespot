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
    timeout /t 10 >nul
    exit /b 1
)

REM Clean up previous builds
echo =^> Cleaning up previous builds...
del /F /Q /A dist\onthespot_win.exe 2>nul
del /F /Q /A dist\onthespot_win_ffm.exe 2>nul

REM Create virtual environment
echo =^> Creating virtual environment...
python -m venv venvwin || (
    echo Failed to create virtual environment. Exiting...
    timeout /t 10 >nul
    exit /b 1
)

REM Activate virtual environment
echo =^> Activating virtual environment...
call venvwin\Scripts\activate.bat || (
    echo Failed to activate virtual environment. Exiting...
    timeout /t 10 >nul
    exit /b 1
)

REM Install dependencies
echo =^> Installing dependencies via pip...
for %%P in (pip wheel winsdk pyinstaller) do (
    python -m pip show %%P >nul || python -m pip install --upgrade %%P || (
        echo Failed to install %%P. Exiting...
        timeout /t 10 >nul
        exit /b 1
    )
)
pip install -r requirements.txt || (
    echo Failed to install dependencies. Exiting...
    timeout /t 10 >nul
    exit /b 1
)

REM Bundle ffmpeg
echo =^> Downloading ffmpeg binary...
mkdir build
curl -L https://github.com/GyanD/codexffmpeg/releases/download/7.1/ffmpeg-7.1-essentials_build.zip -o build\ffmpeg.zip || (
    echo Failed to download ffmpeg. Exiting...
    timeout /t 10 >nul
    exit /b 1
)

powershell -Command "Expand-Archive -Path build\ffmpeg.zip -DestinationPath build\ffmpeg" || (
    echo Failed to extract ffmpeg. Exiting...
    timeout /t 10 >nul
    exit /b 1
)

mkdir ffbin_win

REM Find the extracted ffmpeg directory
set FFMPEG_DIR=
for /d %%D in ("build\ffmpeg\*") do set FFMPEG_DIR=%%D
if defined FFMPEG_DIR (
    xcopy /Y "%FFMPEG_DIR%\bin\ffmpeg.exe" ffbin_win\ >nul 2>&1 || (
        echo Failed to copy ffmpeg binary. Exiting...
        timeout /t 10 >nul
        exit /b 1
    )
) else (
    echo Failed to find extracted ffmpeg directory. Exiting...
    timeout /t 10 >nul
    exit /b 1
)

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
        --add-binary="ffbin_win/ffmpeg.exe;onthespot/bin/ffmpeg" ^
        --paths="src/onthespot" ^
        --name="onthespot_win_ffm" ^
        --icon="src/onthespot/resources/icons/onthespot.png" ^
        src\portable.py || (
        echo PyInstaller build failed. Exiting...
        timeout /t 10 >nul
        exit /b 1
    )
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
        src\portable.py || (
        echo PyInstaller build failed. Exiting...
        timeout /t 10 >nul
        exit /b 1
    )
)

REM Clean up unnecessary files
echo =^> Cleaning up temporary files...
del /F /Q onthespot_win.spec 2>nul
del /F /Q onthespot_win_ffm.spec 2>nul
rmdir /s /q build 2>nul
rmdir /s /q __pycache__ 2>nul
rmdir /s /q venvwin 2>nul
rmdir /s /q ffbin_win 2>nul

echo =^> Done!
timeout /t 10 >nul