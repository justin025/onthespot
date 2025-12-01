#!/bin/bash

echo "========= OnTheSpot macOS Build Script (Fixed) =========="


echo " => Cleaning up previous builds and preparing the environment..."
rm -f ./dist/OnTheSpot.tar.gz
rm -rf build dist venv
mkdir -p build
mkdir -p dist
python3 -m venv venv
source ./venv/bin/activate


echo " => Upgrading pip and installing necessary dependencies..."
venv/bin/pip install --upgrade pip wheel pyinstaller

echo " => Installing dependencies (without librespot first)..."
venv/bin/pip install -r requirements.txt

echo " => Installing librespot-python (latest from GitHub to support librespot v0.7.0)..."
# Try installing from GitHub first (may have newer version with librespot v0.7.0 support)
# Try main branch first, then fallback to PyPI
if venv/bin/pip install --no-deps git+https://github.com/kokarare1212/librespot-python.git@main 2>/dev/null || \
   venv/bin/pip install --no-deps git+https://github.com/kokarare1212/librespot-python.git 2>/dev/null; then
    echo " => Successfully installed librespot-python from GitHub"
else
    # Install the one that has been tested on 30.11.25.
    echo " => GitHub install failed, falling back to PyPI version 0.0.10..."
    venv/bin/pip install --no-deps librespot==0.0.10
fi


echo " => Build FFMPEG (Optional)"
FFBIN="--add-binary=dist/ffmpeg:onthespot/bin/ffmpeg"
if ! [ -f "dist/ffmpeg" ]; then
    curl -L -o build/ffmpeg.zip https://evermeet.cx/ffmpeg/ffmpeg-7.1.zip
    unzip build/ffmpeg.zip -d dist
fi


echo " => Running PyInstaller to create .app package..."
pyinstaller --windowed \
    --hidden-import="zeroconf._utils.ipaddress" \
    --hidden-import="zeroconf._handlers.answers" \
    --add-data="src/onthespot/qt/qtui/*.ui:onthespot/qt/qtui" \
    --add-data="src/onthespot/resources/icons/*.png:onthespot/resources/icons" \
    --add-data="src/onthespot/resources/translations/*.qm:onthespot/resources/translations" \
    $FFBIN \
    --paths="src/onthespot" \
    --name="OnTheSpot" \
    --icon="src/onthespot/resources/icons/onthespot.png" \
    src/portable.py


echo " => Setting executable permissions..."
chmod +x dist/OnTheSpot.app


echo " => Creating dmg..."
mkdir -p dist/dmg
mv dist/OnTheSpot.app dist/dmg/OnTheSpot.app
ln -s /Applications dist/dmg

echo "# Login Issues
Newer versions of macOS have restricted networking features
for apps inside the 'Applications' folder. To login to your
account you will need to:

1. Run the following command in terminal, 'echo \"127.0.0.1 \$HOST\" | sudo tee -a /etc/hosts'

2. Launch the app and click add account before dragging into the applications folder.

3. After successfully logging in you can drag the app into the folder.


# Security Issues
After all this, if you experience an error while trying to launch
the app you will need to open the 'Applications' folder, right-click
the app, and click open anyway." > dist/dmg/readme.txt

hdiutil create -srcfolder dist/dmg -format UDZO -o dist/OnTheSpot.dmg


echo " => Cleaning up temporary files..."
rm -rf __pycache__ build venv *.spec


echo " => Done! .dmg available in 'dist/OnTheSpot.dmg'."
