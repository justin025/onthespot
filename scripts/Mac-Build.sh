#!/bin/bash

# =======================================
# OnTheSpot macOS Build Script
# =======================================
# This script automates the build process of the OnTheSpot macOS application.
# It creates a virtual environment, installs dependencies, and uses PyInstaller
# to build the application, optionally including the FFmpeg binary.

# Exit immediately if a command exits with a non-zero status,
# treat unset variables as an error, and fail if any command in a pipeline fails
set -euo pipefail

# =======================================
# Variables
# =======================================

VENV_DIR="./venv"                                            # Virtual environment directory
DIST_DIR="./dist"                                            # Distribution directory
BUILD_DIR="./build"                                          # Build directory
SPEC_FILES=("onthespot_mac.spec" "onthespot_mac_ffm.spec")   # PyInstaller spec files
APP_NAMES=("onthespot_mac" "onthespot_mac_ffm")              # Application names
FFMPEG_DIR="ffbin_mac"                                       # Directory containing FFmpeg binary
FFMPEG_BINARY="$FFMPEG_DIR/ffmpeg"                           # Path to FFmpeg binary
SOURCE_SCRIPT="src/portable.py"                              # Main Python script to build
ICON_PATH="src/onthespot/resources/onthespot.png"            # Path to application icon
ADDITIONAL_PATHS="src/onthespot"                             # Additional paths to include
HIDDEN_IMPORTS=(                                             # Hidden imports for PyInstaller
    "zeroconf._utils.ipaddress"
    "zeroconf._handlers.answers"
)
DATA_FILES=(                                                # Data files to include in the build
    "src/onthespot/gui/qtui/*.ui:onthespot/gui/qtui"
    "src/onthespot/resources/icons/*.png:onthespot/resources/icons"
    "src/onthespot/resources/themes/*.qss:onthespot/resources/themes"
    "src/onthespot/resources/translations/*.qm:onthespot/resources/translations"
)

# =======================================
# Functions
# =======================================

# Function to print an error message and exit
error_exit() {
    echo "Error: $1" >&2
    exit 1
}

# Function to clean build directories and files
clean_build_dirs() {
    echo "=> Cleaning build directories and files..."
    rm -rf "$BUILD_DIR" "$VENV_DIR" "__pycache__" || true
    for spec_file in "${SPEC_FILES[@]}"; do
        rm -f "$spec_file" || true
    done
    for app_name in "${APP_NAMES[@]}"; do
        rm -rf "$DIST_DIR/$app_name" || true
    done
}

# Function to remove previous app builds
remove_previous_apps() {
    echo "=> Removing previous app builds..."
    for app_name in "${APP_NAMES[@]}"; do
        rm -rf "$DIST_DIR/$app_name.app" || true
    done
}

# Function to create a virtual environment
create_virtual_env() {
    echo "=> Creating virtual environment..."
    python3 -m venv "$VENV_DIR" || error_exit "Failed to create virtual environment."
}

# Function to activate the virtual environment
activate_virtual_env() {
    echo "=> Activating virtual environment..."
    source "$VENV_DIR/bin/activate" || error_exit "Failed to activate virtual environment."
}

# Function to install required Python packages
install_requirements() {
    echo "=> Installing requirements..."
    pip install --upgrade pip || error_exit "Failed to upgrade pip."
    pip install --upgrade wheel setuptools || error_exit "Failed to install build tools."
    pip install --upgrade pyinstaller || error_exit "Failed to install PyInstaller."
    if [ -f "requirements.txt" ]; then
        pip install --upgrade -r requirements.txt || error_exit "Failed to install project requirements."
    else
        echo "Warning: requirements.txt not found. Skipping installation of project dependencies."
    fi
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
        --noconfirm \
        "${hidden_imports_args[@]}" \
        "${data_files_args[@]}" \
        --paths="$ADDITIONAL_PATHS" \
        --name="$app_name" \
        --icon="$ICON_PATH" \
        "${extra_options[@]}" \
        "$SOURCE_SCRIPT" || error_exit "PyInstaller build failed for $app_name."
}

# Function to set executable permissions on the built application
set_executable_permissions() {
    local app_name="$1"
    echo "=> Setting executable permissions for $app_name..."
    if [ -f "$DIST_DIR/$app_name" ]; then
        chmod +x "$DIST_DIR/$app_name" || echo "Warning: Failed to set executable permissions for $app_name."
    fi
}

# =======================================
# Main Script Execution
# =======================================

echo "========= OnTheSpot macOS Build Script ========="

# Check if Python 3 is installed
if ! command -v python3 >/dev/null 2>&1; then
    error_exit "Python 3 is not installed. Please install Python 3 and try again."
fi

# Remove previous app builds and clean build directories
remove_previous_apps
clean_build_dirs

# Create and activate the virtual environment
create_virtual_env
activate_virtual_env

# Install required Python packages
install_requirements

# Check if FFmpeg binary exists, and build accordingly
if [ -f "$FFMPEG_BINARY" ]; then
    echo "=> Found FFmpeg binary in '$FFMPEG_DIR'. Including FFmpeg in the build."
    run_pyinstaller "${APP_NAMES[1]}" \
        --add-binary="$FFMPEG_DIR/*:onthespot/bin/ffmpeg"
    set_executable_permissions "${APP_NAMES[1]}"
else
    echo "=> FFmpeg binary not found. Building without including FFmpeg."
    run_pyinstaller "${APP_NAMES[0]}"
    set_executable_permissions "${APP_NAMES[0]}"
fi

# Deactivate the virtual environment
deactivate || echo "Warning: Failed to deactivate virtual environment."

# Clean up build directories
echo "=> Cleaning up..."
clean_build_dirs

echo "=> Build complete!"

# =======================================
# End of Script
# =======================================
