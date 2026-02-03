@echo off
REM HELLO
set start=%TIME%

rem Check if OnTheSpot.exe is Running
SET "processName=OnTheSpot.exe"
tasklist /FI "IMAGENAME eq %processName%" | findstr /I "%processName%" >nul
if %errorlevel% equ 0 (
    echo %processName% is running. Close the program before building this script.
	pause
	exit /b
) else (
    echo %processName% is not running.
)

set FOLDER_NAME=%cd%
for %%F in ("%cd%") do set FOLDER_NAME=%%~nxF
if /i "%FOLDER_NAME%"=="scripts" (
    echo You are in the scripts folder. Changing to the parent directory...
    cd ..
)

echo ========= OnTheSpot Windows Build Script =========


echo =^> Cleaning up previous builds...
del /F /Q /A dist\onthespot_win_executable.exe


echo =^> Creating virtual environment...
python -m venv venvwin


echo =^> Activating virtual environment...
call venvwin\Scripts\activate.bat


echo =^> Installing dependencies via pip...
python -m pip install --upgrade pip wheel pyinstaller
pip install -r requirements.txt


echo =^> Downloading FFmpeg binary...
mkdir build
curl -L -o build\ffmpeg.zip https://github.com/GyanD/codexffmpeg/releases/download/7.1/ffmpeg-7.1-essentials_build.zip
powershell -Command "Expand-Archive -Path build\ffmpeg.zip -DestinationPath build\ffmpeg"


echo =^> Running PyInstaller to create .exe package...
pyinstaller --onefile --noconsole --noconfirm ^
    --hidden-import="zeroconf._utils.ipaddress" ^
    --hidden-import="zeroconf._handlers.answers" ^
    --add-data="src/onthespot/resources/translations/*.qm;onthespot/resources/translations" ^
    --add-data="src/onthespot/qt/qtui/*.ui;onthespot/qt/qtui" ^
    --add-data="src/onthespot/resources/icons/*.png;onthespot/resources/icons" ^
    --add-binary="build/ffmpeg/ffmpeg-7.1-essentials_build/bin/ffmpeg.exe;onthespot/bin/ffmpeg" ^
    --paths="src/onthespot" ^
    --name="OnTheSpot" ^
    --icon="src/onthespot/resources/icons/onthespot.png" ^
    src\portable.py

echo =^> Cleaning up temporary files...
del /F /Q *.spec
rmdir /s /q build __pycache__ ffbin_win venvwin

echo =^> Done! Executable available as 'dist/OnTheSpot.exe'

rem Calculate compile time
set end=%TIME%
for /F "tokens=1-4 delims=:.," %%a in ("%start%") do (
    set /A "start_h=%%a, start_m=%%b, start_s=%%c, start_cs=%%d"
)
for /F "tokens=1-4 delims=:.," %%a in ("%end%") do (
    set /A "end_h=%%a, end_m=%%b, end_s=%%c, end_cs=%%d"
)
set /A "start_total=(start_h*360000)+(start_m*6000)+(start_s*100)+start_cs"
set /A "end_total=(end_h*360000)+(end_m*6000)+(end_s*100)+end_cs"
set /A "elapsed=end_total-start_total"
rem if %elapsed% lss 0 set /A "elapsed=8640000+elapsed"
set /A "elapsed_h=elapsed/360000, elapsed_m=(elapsed%%360000)/6000, elapsed_s=(elapsed%%6000)/100, elapsed_cs=elapsed%%100"
echo.
echo Script compiled in:    %elapsed_h%h %elapsed_m%m %elapsed_s%s %elapsed_cs%cs
pause