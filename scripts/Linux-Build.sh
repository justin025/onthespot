#!/bin/bash

# OnTheSpot Linux Build Script
# This script builds the OnTheSpot application for Linux using PyInstaller.
# It creates a virtual environment, installs dependencies, and builds the executable.
# Supports including ffmpeg binaries if present.

# Exit immediately if a command exits with a non-zero status
set -e

# =======================================
# <<- Variables ->>
# =======================================

# Directories
VENV_DIR="./venv"
DIST_DIR="./dist"
BUILD_DIR="./build"

# Application names and spec files
APP_NAMES=("onthespot_linux" "onthespot_linux_ffm")
SPEC_FILES=("onthespot_linux.spec" "onthespot_linux_ffm.spec")

# Paths
FFMPEG_DIR="ffbin_nix"
FFMPEG_BINARY="$FFMPEG_DIR/ffmpeg"
SOURCE_SCRIPT="src/portable.py"
ICON_PATH="src/onthespot/resources/icons/onthespot.png"
ADDITIONAL_PATHS="src/onthespot"

# Hidden imports required by PyInstaller
HIDDEN_IMPORTS=(
    "zeroconf._utils.ipaddress"
    "zeroconf._handlers.answers"
)

# Data files to include
DATA_FILES=(
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
}

# Function to remove previous builds
remove_previous_builds() {
    echo "=> Removing previous builds..."
    mkdir -p "$DIST_DIR"
    for app_name in "${APP_NAMES[@]}"; do
        rm -f "$DIST_DIR/$app_name"
        rm -f "$DIST_DIR/$app_name.log"
    done
}

# Function to create virtual environment
create_virtual_env() {
    echo "=> Creating virtual environment..."
    if ! python3 -m venv "$VENV_DIR"; then
        echo "Error: Failed to create virtual environment."
        exit 1
    fi
}

# Function to activate virtual environment
activate_virtual_env() {
    echo "=> Activating virtual environment..."
    if [ -f "$VENV_DIR/bin/activate" ]; then
        # shellcheck source=/dev/null
        source "$VENV_DIR/bin/activate"
    else
        echo "Error: Virtual environment activation script not found."
        exit 1
    fi
}

# Function to install requirements
install_requirements() {
    echo "=> Installing requirements..."
    python -m pip install --upgrade pip
    python -m pip install pyinstaller
    python -m pip install -r requirements.txt
}

# Function to run PyInstaller
run_pyinstaller() {
    local app_name="$1"
    shift
    local extra_options=("$@")
    echo "=> Running PyInstaller for $app_name..."

    # Prepare hidden imports arguments
    local hidden_imports_args=()
    for import in "${HIDDEN_IMPORTS[@]}"; do
        hidden_imports_args+=(--hidden-import="$import")
    done

    # Prepare data files arguments
    local data_files_args=()
    for data in "${DATA_FILES[@]}"; do
        data_files_args+=(--add-data="$data")
    done

    # Run PyInstaller
    python -m PyInstaller --onefile \
        "${hidden_imports_args[@]}" \
        "${data_files_args[@]}" \
        --paths="$ADDITIONAL_PATHS" \
        --name="$app_name" \
        --icon="$ICON_PATH" \
        "${extra_options[@]}" \
        "$SOURCE_SCRIPT"
}

# Function to set executable permissions
set_executable_permissions() {
    local app_name="$1"
    echo "=> Setting executable permissions for $app_name..."
    if [ -f "$DIST_DIR/$app_name" ]; then
        chmod +x "$DIST_DIR/$app_name"
    fi
}

# Function to deactivate virtual environment
deactivate_virtual_env() {
    echo "=> Deactivating virtual environment..."
    if [ "$(type -t deactivate)" = "function" ]; then
        deactivate
    else
        echo "Virtual environment is not active."
    fi
}

# Function to check for required commands
check_dependencies() {
    echo "=> Checking for required commands..."
    local commands=("python3")
    for cmd in "${commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            echo "Error: '$cmd' is not installed. Please install it before running this script."
            exit 1
        fi
    done
}

# Function to display usage
display_usage() {
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --clean          Clean build directories and exit"
    echo "  --help           Display this help message and exit"
    echo
    echo "This script builds the OnTheSpot application for Linux using PyInstaller."
    echo "It creates a virtual environment, installs dependencies, and builds the executable."
    echo "Supports including ffmpeg binaries if present in the '$FFMPEG_DIR' directory."
}

# Function to parse command-line arguments
parse_arguments() {
    for arg in "$@"; do
        case "$arg" in
            --clean)
                clean_build_dirs
                echo "=> Cleaned build directories."
                exit 0
                ;;
            --help)
                display_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $arg"
                display_usage
                exit 1
                ;;
        esac
    done
}

# =======================================
# <<- Main Script Execution ->>
# =======================================

echo "========= OnTheSpot Linux Build Script ========="

# Parse command-line arguments
parse_arguments "$@"

# Check for required commands
check_dependencies

# Remove previous builds and clean directories
remove_previous_builds
clean_build_dirs

# Create and activate virtual environment
create_virtual_env
activate_virtual_env

# Install requirements
install_requirements

# Ensure 'dist' directory exists
mkdir -p "$DIST_DIR"

# Check if ffmpeg binary exists
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

# Deactivate virtual environment
deactivate_virtual_env

# Clean up build directories
echo "=> Cleaning up..."
clean_build_dirs

echo "=> Build complete! Executables are located in the '$DIST_DIR' directory."
