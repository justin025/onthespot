#!/bin/bash

# OnTheSpot AppImage Build Script
# This script builds the OnTheSpot application into an AppImage.

set -e  # Exit immediately if a command exits with a non-zero status.

echo "========= OnTheSpot AppImage Build Script ========="

# =======================================
# <<- Variables ->>
# =======================================

# Directories
BUILD_DIR="build"
APP_DIR="OnTheSpot.AppDir"
DIST_DIR="dist"

# URLs and Filenames
PYTHON_APPIMAGE_URL="https://github.com/niess/python-appimage/releases/download/python3.12/python3.12.3-cp312-cp312-manylinux2014_x86_64.AppImage"
PYTHON_APPIMAGE_NAME="$(basename "$PYTHON_APPIMAGE_URL")"
APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
APPIMAGETOOL_NAME="$(basename "$APPIMAGETOOL_URL")"
FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
FFMPEG_TAR="$(basename "$FFMPEG_URL")"
FFMPEG_DIR="$APP_DIR/usr/bin"

# =======================================
# <<- Functions ->>
# =======================================

# Function to clean up previous builds
cleanup() {
    echo "=> Cleaning up previous builds..."
    rm -rf "$DIST_DIR" "$BUILD_DIR"
}

# Function to download dependencies
download_dependencies() {
    echo "=> Fetching Dependencies..."
    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR" || exit 1

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
}

# Function to extract Python AppImage
extract_python_appimage() {
    echo "=> Extracting Python AppImage..."
    ./"$PYTHON_APPIMAGE_NAME" --appimage-extract
    mv squashfs-root "$APP_DIR"
}

# Function to build OnTheSpot wheel
build_wheel() {
    echo "=> Building OnTheSpot wheel..."
    cd .. || exit 1
    "./$BUILD_DIR/$APP_DIR/AppRun" -m pip install --upgrade pip setuptools wheel
    "./$BUILD_DIR/$APP_DIR/AppRun" -m build
}

# Function to prepare AppDir
prepare_appdir() {
    echo "=> Preparing OnTheSpot AppImage..."
    cd "$BUILD_DIR" || exit 1

    # Install requirements and the built wheel into the AppDir
    "$APP_DIR/AppRun" -m pip install -r ../requirements.txt
    "$APP_DIR/AppRun" -m pip install ../dist/onthespot-*-py3-none-any.whl

    # Clean up unnecessary files
    rm "$APP_DIR"/AppRun
    rm "$APP_DIR"/.DirIcon
    rm "$APP_DIR"/python.png
    rm "$APP_DIR"/*.desktop

    # Add application icon and desktop file
    cp ../src/onthespot/resources/icons/onthespot.svg "$APP_DIR"/onthespot.svg
    cp ../src/onthespot/resources/org.eu.casualsnek.onthespot.desktop "$APP_DIR"/org.eu.casualsnek.onthespot.desktop

    # Create AppRun script
    create_apprun_script
}

# Function to create AppRun script
create_apprun_script() {
    echo "=> Creating AppRun script..."
    cat << 'EOF' > "$APP_DIR/AppRun"
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
    chmod +x "$APP_DIR/AppRun"
}

# Function to add FFmpeg binaries
add_ffmpeg() {
    echo "=> Adding FFmpeg and FFplay binaries..."
    mkdir -p "$FFMPEG_DIR"
    if [ ! -f "$FFMPEG_TAR" ]; then
        wget "$FFMPEG_URL"
    fi
    tar -xf "$FFMPEG_TAR" --wildcards --strip-components=1 --no-anchored 'ffmpeg' 'ffplay' -C "$FFMPEG_DIR"
    chmod +x "$FFMPEG_DIR"/ffmpeg "$FFMPEG_DIR"/ffplay
    rm "$FFMPEG_TAR"
}

# Function to build the AppImage
build_appimage() {
    echo "=> Building OnTheSpot AppImage..."
    cd "$BUILD_DIR" || exit 1
    ./"$APPIMAGETOOL_NAME" "$APP_DIR"

    # Move the AppImage to the dist directory
    mkdir -p "../$DIST_DIR"
    mv OnTheSpot-x86_64.AppImage "../$DIST_DIR/OnTheSpot-x86_64.AppImage"

    echo "=> Build complete. AppImage is located in the '$DIST_DIR' directory."
}

# Function to prompt user to add custom files (optional)
add_custom_files() {
    echo "=> Do you want to add any custom files or configurations? (y/n)"
    read -r add_custom
    if [ "$add_custom" = "y" ]; then
        echo "Please add your custom files to the '$APP_DIR' directory now."
        echo "Press Enter when you're done."
        read -r
    fi
}

# =======================================
# <<- Main Script Execution ->>
# =======================================

# 1. Clean up any previous builds
cleanup

# 2. Download necessary dependencies
download_dependencies

# 3. Extract Python AppImage to create AppDir
extract_python_appimage

# 4. Build the OnTheSpot wheel package
build_wheel

# 5. Prepare the AppDir by installing dependencies and cleaning up
prepare_appdir

# 6. Add FFmpeg binaries to the AppDir
add_ffmpeg

# 7 Allow the user to add custom files or configurations(Optional)
add_custom_files

# 8. Build the final AppImage
build_appimage
