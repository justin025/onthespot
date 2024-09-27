#!/bin/bash

echo "========= OnTheSpot Linux Build Script ========="

# Check the current folder and change directory if necessary
FOLDER_NAME=$(basename "$PWD")

if [ "$FOLDER_NAME" == "scripts" ]; then
    echo "You are in the scripts folder. Changing to the parent directory..."
    cd ..
elif [ "$FOLDER_NAME" != "onthespot" ]; then
    echo "Make sure that you are inside the project folder. Current folder is: $FOLDER_NAME"
    exit 1
fi

# Clean up previous builds
echo " => Cleaning up!"
rm -f ./dist/onthespot_linux ./dist/onthespot_linux_ffm

# Create virtual environment
echo " => Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo " => Activating virtual environment..."
source ./venv/bin/activate

# Upgrade pip and install dependencies using Bash
echo " => Upgrading pip and installing necessary dependencies..."
venv/bin/pip install --upgrade pip wheel winsdk pyinstaller

# Install project-specific dependencies
echo " => Installing project-specific dependencies..."
venv/bin/pip install -r requirements.txt

# Check for FFmpeg and set build options
if [ -f "ffbin_nix/ffmpeg" ]; then
    echo " => Found 'ffbin_nix' directory and ffmpeg binary. Including FFmpeg in the build."
    FFBIN="--add-binary=ffbin_nix/*:onthespot/bin/ffmpeg"
    NAME="onthespot_linux_ffm"
else
    echo " => FFmpeg binary not found. Building without it."
    NAME="onthespot_linux"
    FFBIN=""
fi

# Run PyInstaller
pyinstaller --onefile \
    --hidden-import="zeroconf._utils.ipaddress" \
    --hidden-import="zeroconf._handlers.answers" \
    --add-data="src/onthespot/gui/qtui/*.ui:onthespot/gui/qtui" \
    --add-data="src/onthespot/resources/icons/*.png:onthespot/resources/icons" \
    --add-data="src/onthespot/resources/themes/*.qss:onthespot/resources/themes" \
    --add-data="src/onthespot/resources/translations/*.qm:onthespot/resources/translations" \
    $FFBIN \
    --paths="src/onthespot" \
    --name=$NAME \
    --icon="src/onthespot/resources/icons/onthespot.png" \
    src/portable.py

# Set executable permissions
echo " => Setting executable permissions..."
[ -f ./dist/onthespot_linux ] && chmod +x ./dist/onthespot_linux
[ -f ./dist/onthespot_linux_ffm ] && chmod +x ./dist/onthespot_linux_ffm

# Clean up unnecessary files
echo " => Cleaning up temporary files..."
rm -rf __pycache__ build venv *.spec

echo " => Done!"
