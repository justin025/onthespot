#!/bin/bash

# =======================================
# OnTheSpot Linux Build Script
# =======================================
# This script builds the OnTheSpot application for Linux using PyInstaller.
# It creates a virtual environment, installs dependencies, and builds the executable.
# Supports including FFmpeg binaries if present.

# Exit immediately if a command exits with a non-zero status,
# treat unset variables as an error, and fail if any command in a pipeline fails
set -euo pipefail

# =======================================
# Variables
# =======================================

# Directories
VENV_DIR="./venv"                                # Virtual environment directory
DIST_DIR="./dist"                                # Distribution directory
BUILD_DIR="./build"                              # Build directory

# Application names and spec files
APP_NAMES=("onthespot_linux" "onthespot_linux_ffm")             # Application names
SPEC_FILES=("onthespot_linux.spec" "onthespot_linux_ffm.spec")  # PyInstaller spec files

# Paths
FFMPEG_DIR="ffbin_nix"                                   # Directory containing FFmpeg binary
FFMPEG_BINARY="$FFMPEG_DIR/ffmpeg"                       # Path to FFmpeg binary
SOURCE_SCRIPT="src/portable.py"                          # Main Python script to build
ICON_PATH="src/onthespot/resources/icons/onthespot.png"  # Path to application icon
ADDITIONAL_PATHS="src/onthespot"                         # Additional paths to include

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
}

# Function to remove previous builds
remove_previous_builds() {
    echo "=> Removing previous builds..."
    mkdir -p "$DIST_DIR"
    for app_name in "${APP_NAMES[@]}"; do
        rm -f "$DIST_DIR/$app_name" || true
        rm -f "$DIST_DIR/$app_name.log" || true
    done
}

# Function to create virtual environment
create_virtual_env() {
    echo "=> Creating virtual environment..."
    python3 -m venv "$VENV_DIR" || error_exit "Failed to create virtual environment."
}

# Function to activate virtual environment
activate_virtual_env() {
    echo "=> Activating virtual environment..."
    if [ -f "$VENV_DIR/bin/activate" ]; then
        # shellcheck source=/dev/null
        source "$VENV_DIR/bin/activate" || error_exit "Failed to activate virtual environment."
    else
        error_exit "Virtual environment activation script not found."
    fi
}

# Function to install requirements
install_requirements() {
    echo "=> Installing requirements..."
    python -m pip install --upgrade pip || error_exit "Failed to upgrade pip."
    python -m pip install --upgrade wheel setuptools || error_exit "Failed to install build tools."
    python -m pip install --upgrade pyinstaller || error_exit "Failed to install PyInstaller."
    if [ -f "requirements.txt" ]; then
        python -m pip install --upgrade -r requirements.txt || error_exit "Failed to install project requirements."
    else
        echo "Warning: requirements.txt not found. Skipping installation of project dependencies."
    fi
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
    pyinstaller --onefile \
        --noconfirm \
        "${hidden_imports_args[@]}" \
        "${data_files_args[@]}" \
        --paths="$ADDITIONAL_PATHS" \
        --name="$app_name" \
        --icon="$ICON_PATH" \
        "${extra_options[@]}" \
        "$SOURCE_SCRIPT" || error_exit "PyInstaller build failed for $app_name."
}

# Function to set executable permissions
set_executable_permissions() {
    local app_name="$1"
    echo "=> Setting executable permissions for $app_name..."
    if [ -f "$DIST_DIR/$app_name" ]; then
        chmod +x "$DIST_DIR/$app_name" || echo "Warning: Failed to set executable permissions for $app_name."
    fi
}

# Function to deactivate virtual environment
deactivate_virtual_env() {
    echo "=> Deactivating virtual environment..."
    if [ "$(type -t deactivate)" = "function" ]; then
        deactivate || echo "Warning: Failed to deactivate virtual environment."
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
            error_exit "'$cmd' is not installed. Please install it before running this script."
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
    echo "Supports including FFmpeg binaries if present in the '$FFMPEG_DIR' directory."
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
# Main Script Execution
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

# Check if FFmpeg binary exists
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

# Deactivate virtual environment
deactivate_virtual_env

# Clean up build directories
echo "=> Cleaning up..."
clean_build_dirs

echo "=> Build complete! Executables are located in the '$DIST_DIR' directory."

# =======================================
# End of Script
# =======================================
