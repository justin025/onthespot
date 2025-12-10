#!/bin/bash

echo "========= OnTheSpot macOS Build Script =========="

set -e  # Stop on error

echo " => Cleaning previous builds..."
rm -f ./dist/OnTheSpot.tar.gz
rm -rf build dist venv
mkdir -p build dist

echo " => Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo " => Installing dependencies..."
pip install --upgrade pip wheel pyinstaller
pip install -r requirements.txt

echo " => Running PyInstaller (NO FFMPEG)..."
pyinstaller --windowed \
    --hidden-import="zeroconf._utils.ipaddress" \
    --hidden-import="zeroconf._handlers.answers" \
    --add-data="src/onthespot/qt/qtui/*.ui:onthespot/qt/qtui" \
    --add-data="src/onthespot/resources/icons/*.png:onthespot/resources/icons" \
    --add-data="src/onthespot/resources/translations/*.qm:onthespot/resources/translations" \
    --paths="src/onthespot" \
    --name="OnTheSpot" \
    --icon="src/onthespot/resources/icons/onthespot.png" \
    src/portable.py

echo " => Setting permissions..."
chmod +x dist/OnTheSpot.app

echo " => Preparing DMG structure..."
mkdir -p dist/dmg
mv dist/OnTheSpot.app dist/dmg/OnTheSpot.app
ln -s /Applications dist/dmg/Applications

cat > dist/dmg/readme.txt << 'EOF'
# Login Issues
Newer versions of macOS restrict networking for apps inside the 'Applications' folder.
To login:

1. Run: echo "127.0.0.1 $HOST" | sudo tee -a /etc/hosts
2. Launch the app and add the account before moving it to Applications.
3. After login, move the app to the Applications folder.

# Security Issues
If blocked, right-click the app and choose "Open anyway".
EOF

echo " => Creating DMG..."
hdiutil create -srcfolder dist/dmg -format UDZO -o dist/OnTheSpot.dmg

echo " => Cleaning temporary files..."
rm -rf build venv *.spec dist/dmg

echo " => Done! .dmg created at 'dist/OnTheSpot.dmg'."
