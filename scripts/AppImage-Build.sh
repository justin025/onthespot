#!/bin/bash

# OnTheSpot AppImage Build Script
# This script builds the OnTheSpot application into an AppImage.

set -e  # Exit immediately if a command exits with a non-zero status.

echo "========= OnTheSpot AppImage Build Script =========="

# Variables
BUILD_DIR="build"
APP_DIR="OnTheSpot.AppDir"
DIST_DIR="dist"
PYTHON_APPIMAGE_URL="https://github.com/niess/python-appimage/releases/download/python3.12/python3.12.3-cp312-cp312-manylinux2014_x86_64.AppImage"
PYTHON_APPIMAGE_NAME="$(basename $PYTHON_APPIMAGE_URL)"
APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
APPIMAGETOOL_NAME="$(basename $APPIMAGETOOL_URL)"
FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
FFMPEG_TAR="$(basename $FFMPEG_URL)"
FFMPEG_DIR="$APP_DIR/usr/bin"

# Clean up previous builds
echo "=> Cleaning up previous builds..."
rm -rf "$DIST_DIR" "$BUILD_DIR"

# Create build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Download appimagetool
echo "=> Downloading AppImageTool..."
if [ ! -f "$APPIMAGETOOL_NAME" ]; then
    wget "$APPIMAGETOOL_URL"
    chmod +x "$APPIMAGETOOL_NAME"
fi

# Download Python AppImage
echo "=> Downloading Python AppImage..."
if [ ! -f "$PYTHON_APPIMAGE_NAME" ]; then
    wget "$PYTHON_APPIMAGE_URL"
    chmod +x "$PYTHON_APPIMAGE_NAME"
fi

# Extract Python AppImage
echo "=> Extracting Python AppImage..."
./"$PYTHON_APPIMAGE_NAME" --appimage-extract
mv squashfs-root "$APP_DIR"

# Build OnTheSpot wheel
echo "=> Building OnTheSpot wheel..."
cd ..
./"$BUILD_DIR"/"$APP_DIR"/AppRun -m pip install --upgrade pip setuptools wheel
./"$BUILD_DIR"/"$APP_DIR"/AppRun -m build

# Prepare OnTheSpot AppImage
echo "=> Preparing OnTheSpot AppImage..."
cd "$BUILD_DIR"
"$APP_DIR"/AppRun -m pip install -r ../requirements.txt
"$APP_DIR"/AppRun -m pip install ../dist/onthespot-*-py3-none-any.whl

# Clean up unnecessary files
rm "$APP_DIR"/AppRun
rm "$APP_DIR"/.DirIcon
rm "$APP_DIR"/python.png
rm "$APP_DIR"/*.desktop

# Add application icon and desktop file
cp ../src/onthespot/resources/icon.svg "$APP_DIR"/casual_onthespot.svg
cp ../src/onthespot/resources/org.eu.casualsnek.onthespot.desktop "$APP_DIR"/org.eu.casualsnek.onthespot.desktop

# Create AppRun script
cat << 'EOF' > "$APP_DIR"/AppRun
#!/bin/bash

HERE="$(dirname "$(readlink -f "${0}")")"

# Export PATH
export PATH="$HERE/usr/bin:$PATH"

# Export Tcl/Tk
export TCL_LIBRARY="${APPDIR}/usr/share/tcltk/tcl8.6"
export TK_LIBRARY="${APPDIR}/usr/share/tcltk/tk8.6"
export TKPATH="${TK_LIBRARY}"

# Export SSL certificate
export SSL_CERT_FILE="${APPDIR}/opt/_internal/certs.pem"

# Call OnTheSpot
"$HERE/opt/python3.12/bin/python3.12" -m onthespot "$@"
EOF
chmod +x "$APP_DIR"/AppRun

# Add FFmpeg and FFplay binaries
echo "=> Adding FFmpeg and FFplay binaries..."
mkdir -p "$FFMPEG_DIR"
if [ ! -f "$FFMPEG_TAR" ]; then
    wget "$FFMPEG_URL"
fi
tar -xf "$FFMPEG_TAR" --wildcards --strip-components=1 --no-anchored 'ffmpeg' 'ffplay' -C "$FFMPEG_DIR"
chmod +x "$FFMPEG_DIR"/ffmpeg "$FFMPEG_DIR"/ffplay
rm "$FFMPEG_TAR"

# Build OnTheSpot AppImage
echo "=> Building OnTheSpot AppImage..."
./"$APPIMAGETOOL_NAME" "$APP_DIR"

# Move the AppImage to the dist directory
mkdir -p "../$DIST_DIR"
mv OnTheSpot-x86_64.AppImage "../$DIST_DIR"/OnTheSpot-x86_64.AppImage

echo "=> Build complete. AppImage is located in the '$DIST_DIR' directory."
