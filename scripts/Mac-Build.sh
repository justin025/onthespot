#!/bin/bash

# Exit immediately if a command exits with a non-zero status,
# treat unset variables as an error, and fail if any command in a pipeline fails
set -euo pipefail

# OnTheSpot MacOS Build Script
# This script automates the build process of the OnTheSpot MacOS application.
# It creates a virtual environment, installs dependencies, and uses PyInstaller
# to build the application, optionally including the ffmpeg binary.

# =======================================
# <<- Variables ->>
# =======================================

VENV_DIR="./venv"                       # Virtual environment directory
DIST_DIR="./dist"                       # Distribution directory
BUILD_DIR="./build"                     # Build directory
SPEC_FILES=("onthespot_mac.spec" "onthespot_mac_ffm.spec")    # PyInstaller spec files
APP_NAMES=("onthespot_mac" "onthespot_mac_ffm")               # Application names
FFMPEG_DIR="ffbin_mac"                  # Directory containing ffmpeg binary
FFMPEG_BINARY="$FFMPEG_DIR/ffmpeg"      # Path to ffmpeg binary
SOURCE_SCRIPT="src/portable.py"         # Main Python script to build
ICON_PATH="src/onthespot/resources/onthespot.png"             # Path to application icon
ADDITIONAL_PATHS="src/onthespot"        # Additional paths to include
HIDDEN_IMPORTS=(                        # Hidden imports for PyInstaller
    "zeroconf._utils.ipaddress"
    "zeroconf._handlers.answers"
)
DATA_FILES=(                            # Data files to include in the build
    "src/onthespot/gui/qtui/*.ui:onthespot/gui/qtui"
    "src/onthespot/resources/icons/*.png:onthespot/resources/icons"
    "src/onthespot/resources/themes/*.qss:onthespot/resources/themes"
    "src/onthespot/resources/translations/*.qm:onthespot/resources/translations"
)

# =======================================
# <<- Functions ->>
# =======================================

# Function to clean build directories and files
clean_build_dirs() {
    echo "=> Cleaning build directories and files..."
    rm -rf "$BUILD_DIR" "$VENV_DIR" "__pycache__"
    for spec_file in "${SPEC_FILES[@]}"; do
        rm -f "$spec_file"
    done
    for app_name in "${APP_NAMES[@]}"; do
        rm -rf "$DIST_DIR/$app_name"
    done
}

# Function to remove previous app builds
remove_previous_apps() {
    echo "=> Removing previous app builds..."
    for app_name in "${APP_NAMES[@]}"; do
        rm -rf "$DIST_DIR/$app_name.app"
    done
}

# Function to create a virtual environment
create_virtual_env() {
    echo "=> Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
}

# Function to activate the virtual environment
activate_virtual_env() {
    echo "=> Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
}

# Function to install required Python packages
install_requirements() {
    echo "=> Installing requirements..."
    pip install --upgrade pip
    pip install pyinstaller
    pip install -r requirements.txt
}

# Function to run PyInstaller to build the application
run_pyinstaller() {
    local app_name="$1"
    shift
    local extra_options=("$@")
    echo "=> Running PyInstaller for $app_name..."
    local hidden_imports_args=()
    for import in "${HIDDEN_IMPORTS[@]}"; do
        hidden_imports_args+=(--hidden-import="$import")
    done
    local data_files_args=()
    for data in "${DATA_FILES[@]}"; do
        data_files_args+=(--add-data="$data")
    done
    pyinstaller --windowed \
        "${hidden_imports_args[@]}" \
        "${data_files_args[@]}" \
        --paths="$ADDITIONAL_PATHS" \
        --name="$app_name" \
        --icon="$ICON_PATH" \
        "${extra_options[@]}" \
        "$SOURCE_SCRIPT"
}

# Function to set executable permissions on the built application
set_executable_permissions() {
    local app_name="$1"
    echo "=> Setting executable permissions for $app_name..."
    if [ -f "$DIST_DIR/$app_name" ]; then
        chmod +x "$DIST_DIR/$app_name"
    fi
}

# =======================================
# <<- Main Script Execution ->>
# =======================================

echo "========= OnTheSpot macOS Build Script ========="

# Remove previous app builds and clean build directories
remove_previous_apps
clean_build_dirs

# Create and activate the virtual environment
create_virtual_env
activate_virtual_env

# Install required Python packages
install_requirements

# Check if ffmpeg binary exists, and build accordingly
if [ -f "$FFMPEG_BINARY" ]; then
    echo "=> Found ffmpeg binary in '$FFMPEG_DIR'. Including ffmpeg in the build."
    run_pyinstaller "${APP_NAMES[1]}" \
        --add-binary="$FFMPEG_DIR/*:onthespot/bin/ffmpeg"
    set_executable_permissions "${APP_NAMES[1]}"
else
    echo "=> ffmpeg binary not found. Building without including ffmpeg."
    run_pyinstaller "${APP_NAMES[0]}"
    set_executable_permissions "${APP_NAMES[0]}"
fi

# Deactivate the virtual environment
deactivate

# Clean up build directories
echo "=> Cleaning up..."
clean_build_dirs

echo "=> Build complete!"
