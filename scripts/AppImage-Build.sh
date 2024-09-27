#!/bin/bash

# =======================================
# OnTheSpot AppImage Build Script
# =======================================
# This script builds the OnTheSpot application into an AppImage.

# Exit immediately if a command exits with a non-zero status,
# treat unset variables as an error, and fail if any command in a pipeline fails
set -euo pipefail

echo "========= OnTheSpot AppImage Build Script ========="

# =======================================
# Variables
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
# Functions
# =======================================

# Function to print an error message and exit
error_exit() {
    echo "Error: $1" >&2
    exit 1
}

# Function to check for required commands
check_dependencies() {
    echo "=> Checking for required commands..."
    local commands=("wget" "tar" "readlink" "dirname" "realpath")
    for cmd in "${commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            error_exit "'$cmd' is not installed. Please install it before running this script."
        fi
    done
}

# Function to clean up previous builds
cleanup() {
    echo "=> Cleaning up previous builds..."
    rm -rf "$DIST_DIR" "$BUILD_DIR" || true
}

# Function to download dependencies
download_dependencies() {
    echo "=> Fetching dependencies..."
    mkdir -p "$BUILD_DIR"
    pushd "$BUILD_DIR" >/dev/null || error_exit "Failed to enter build directory."

    # Download appimagetool
    echo "=> Downloading appimagetool..."
    if [ ! -f "$APPIMAGETOOL_NAME" ]; then
        wget -q --show-progress "$APPIMAGETOOL_URL" || error_exit "Failed to download appimagetool."
        chmod +x "$APPIMAGETOOL_NAME"
    else
        echo "=> appimagetool already downloaded."
    fi

    # Download Python AppImage
    echo "=> Downloading Python AppImage..."
    if [ ! -f "$PYTHON_APPIMAGE_NAME" ]; then
        wget -q --show-progress "$PYTHON_APPIMAGE_URL" || error_exit "Failed to download Python AppImage."
        chmod +x "$PYTHON_APPIMAGE_NAME"
    else
        echo "=> Python AppImage already downloaded."
    fi

    popd >/dev/null
}

# Function to extract Python AppImage
extract_python_appimage() {
    echo "=> Extracting Python AppImage..."
    pushd "$BUILD_DIR" >/dev/null || error_exit "Failed to enter build directory."
    ./"$PYTHON_APPIMAGE_NAME" --appimage-extract || error_exit "Failed to extract Python AppImage."
    mv squashfs-root "$APP_DIR" || error_exit "Failed to move extracted AppImage."
    popd >/dev/null
}

# Function to build OnTheSpot wheel
build_wheel() {
    echo "=> Building OnTheSpot wheel..."
    "./$BUILD_DIR/$APP_DIR/AppRun" -m pip install --upgrade pip setuptools wheel || error_exit "Failed to upgrade pip and install build tools."
    "./$BUILD_DIR/$APP_DIR/AppRun" -m pip install --upgrade build || error_exit "Failed to install build module."
    "./$BUILD_DIR/$APP_DIR/AppRun" -m build || error_exit "Failed to build the wheel."
}

# Function to prepare AppDir
prepare_appdir() {
    echo "=> Preparing OnTheSpot AppDir..."
    pushd "$BUILD_DIR" >/dev/null || error_exit "Failed to enter build directory."

    # Install requirements and the built wheel into the AppDir
    "$APP_DIR/AppRun" -m pip install -r ../requirements.txt || error_exit "Failed to install requirements."
    "$APP_DIR/AppRun" -m pip install ../dist/onthespot-*-py3-none-any.whl || error_exit "Failed to install OnTheSpot wheel."

    # Clean up unnecessary files
    rm -f "$APP_DIR"/AppRun
    rm -f "$APP_DIR"/.DirIcon
    rm -f "$APP_DIR"/python.png
    rm -f "$APP_DIR"/*.desktop

    # Add application icon and desktop file
    cp ../src/onthespot/resources/icons/onthespot.svg "$APP_DIR"/onthespot.svg || error_exit "Failed to copy icon."
    cp ../src/onthespot/resources/org.eu.casualsnek.onthespot.desktop "$APP_DIR"/org.eu.casualsnek.onthespot.desktop || error_exit "Failed to copy desktop file."

    # Create AppRun script
    create_apprun_script

    popd >/dev/null
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
    chmod +x "$APP_DIR/AppRun" || error_exit "Failed to make AppRun script executable."
}

# Function to add FFmpeg binaries
add_ffmpeg() {
    echo "=> Adding FFmpeg and FFplay binaries..."
    mkdir -p "$FFMPEG_DIR"
    pushd "$FFMPEG_DIR" >/dev/null || error_exit "Failed to enter FFmpeg directory."
    if [ ! -f "ffmpeg" ] || [ ! -f "ffplay" ]; then
        if [ ! -f "../../$FFMPEG_TAR" ]; then
            wget -q --show-progress "$FFMPEG_URL" -O "../../$FFMPEG_TAR" || error_exit "Failed to download FFmpeg."
        else
            echo "=> FFmpeg archive already downloaded."
        fi
        tar -xf "../../$FFMPEG_TAR" --wildcards --strip-components=1 --no-anchored 'ffmpeg' 'ffplay' || error_exit "Failed to extract FFmpeg binaries."
        chmod +x ffmpeg ffplay || error_exit "Failed to set execute permissions on FFmpeg binaries."
        rm -f "../../$FFMPEG_TAR"
    else
        echo "=> FFmpeg binaries already present."
    fi
    popd >/dev/null
}

# Function to build the AppImage
build_appimage() {
    echo "=> Building OnTheSpot AppImage..."
    pushd "$BUILD_DIR" >/dev/null || error_exit "Failed to enter build directory."
    ./"$APPIMAGETOOL_NAME" "$APP_DIR" || error_exit "Failed to build AppImage."

    # Move the AppImage to the dist directory
    mkdir -p "../$DIST_DIR"
    mv OnTheSpot-x86_64.AppImage "../$DIST_DIR/OnTheSpot-x86_64.AppImage" || error_exit "Failed to move AppImage to dist directory."

    echo "=> Build complete. AppImage is located in the '$DIST_DIR' directory."
    popd >/dev/null
}

# Function to prompt user to add custom files (optional)
add_custom_files() {
    echo "=> Do you want to add any custom files or configurations? (y/n)"
    read -r add_custom
    if [ "$add_custom" = "y" ] || [ "$add_custom" = "Y" ]; then
        echo "Please add your custom files to the '$BUILD_DIR/$APP_DIR' directory now."
        echo "Press Enter when you're done."
        read -r
    fi
}

# =======================================
# Main Script Execution
# =======================================

# Check for required commands
check_dependencies

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

# 7. Allow the user to add custom files or configurations (Optional)
add_custom_files

# 8. Build the final AppImage
build_appimage
