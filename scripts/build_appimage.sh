#!/bin/bash

echo "========= OnTheSpot AppImage Build Script ========="

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
rm -rf dist build

# Fetch Dependencies
echo " => Fetching Dependencies"
mkdir -p build && cd build

# Download AppImage Tool and Python AppImage
wget -q https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage

wget -q https://github.com/niess/python-appimage/releases/download/python3.12/python3.12.3-cp312-cp312-manylinux2014_x86_64.AppImage
chmod +x python3.12.3-cp312-cp312-manylinux2014_x86_64.AppImage

# Extract Python AppImage
echo " => Extracting Python AppImage"
./python3.12.3-cp312-cp312-manylinux2014_x86_64.AppImage --appimage-extract
mv squashfs-root OnTheSpot.AppDir

# Build OnTheSpot Wheel
echo " => Building OnTheSpot wheel"
cd ..
build/OnTheSpot.AppDir/AppRun -m build

# Upgrade pip and install necessary dependencies
echo " => Upgrading pip and installing necessary dependencies..."
build/OnTheSpot.AppDir/AppRun -m pip install --upgrade pip wheel winsdk pyinstaller

# Prepare OnTheSpot AppImage
echo " => Preparing OnTheSpot AppImage"
cd build
OnTheSpot.AppDir/AppRun -m pip install -r ../requirements.txt
OnTheSpot.AppDir/AppRun -m pip install ../dist/onthespot-*-py3-none-any.whl

# Clean up unnecessary files
rm OnTheSpot.AppDir/AppRun OnTheSpot.AppDir/.DirIcon OnTheSpot.AppDir/python.png OnTheSpot.AppDir/python3.12.3.desktop

# Copy resources
cp ../src/onthespot/resources/icons/onthespot.svg OnTheSpot.AppDir/onthespot.svg
cp ../src/onthespot/resources/org.eu.casualsnek.onthespot.desktop OnTheSpot.AppDir/org.eu.casualsnek.onthespot.desktop

# Create AppRun script
cat << 'EOF' > OnTheSpot.AppDir/AppRun
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
# Export PATH
export PATH=$HERE/usr/bin:$PATH
# Export TCl/Tk
export TCL_LIBRARY="${APPDIR}/usr/share/tcltk/tcl8.6"
export TK_LIBRARY="${APPDIR}/usr/share/tcltk/tk8.6"
export TKPATH="${TK_LIBRARY}"
# Export SSL certificate
export SSL_CERT_FILE="${APPDIR}/opt/_internal/certs.pem"
# Call OnTheSpot
"$HERE/opt/python3.12/bin/python3.12" -m onthespot "$@"
EOF
chmod +x OnTheSpot.AppDir/AppRun

# FFmpeg notice
echo ' => ffmpeg and ffplay need to be manually added to OnTheSpot.AppDir/usr/bin.'
echo ' => Binaries can be found at https://johnvansickle.com/ffmpeg/'

# Ask user about ffmpeg binaries
read -p ' => Done adding ffmpeg binaries? (y/n): ' ffmpeg
if [[ "$ffmpeg" == "y" ]]; then
    echo " => Building OnTheSpot AppImage"
    ./appimagetool-x86_64.AppImage OnTheSpot.AppDir
    mv OnTheSpot-x86_64.AppImage ../dist/OnTheSpot-x86_64.AppImage
    echo " => Done!"
else
    echo " => Exiting without building AppImage."
fi
