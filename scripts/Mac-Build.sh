#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Variables
VENV_DIR="./venv"
DIST_DIR="./dist"
BUILD_DIR="./build"
SPEC_FILES=("onthespot_mac.spec" "onthespot_mac_ffm.spec")
APP_NAMES=("onthespot_mac" "onthespot_mac_ffm")
FFMPEG_DIR="ffbin_mac"
FFMPEG_BINARY="$FFMPEG_DIR/ffmpeg"
SOURCE_SCRIPT="src/portable.py"
ICON_PATH="src/onthespot/resources/onthespot.png"
ADDITIONAL_PATHS="src/onthespot"
HIDDEN_IMPORTS=(
    "zeroconf._utils.ipaddress"
    "zeroconf._handlers.answers"
)
DATA_FILES=(
    "src/onthespot/gui/qtui/*.ui:onthespot/gui/qtui"
    "src/onthespot/resources/icons/*.png:onthespot/resources/icons"
    "src/onthespot/resources/themes/*.qss:onthespot/resources/themes"
    "src/onthespot/resources/translations/*.qm:onthespot/resources/translations"
)

# Functions
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

remove_previous_apps() {
    echo "=> Removing previous app builds..."
    for app_name in "${APP_NAMES[@]}"; do
        rm -rf "$DIST_DIR/$app_name.app"
    done
}

create_virtual_env() {
    echo "=> Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
}

activate_virtual_env() {
    echo "=> Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
}

install_requirements() {
    echo "=> Installing requirements..."
    pip install --upgrade pip
    pip install pyinstaller
    pip install -r requirements.txt
}

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

set_executable_permissions() {
    local app_name="$1"
    echo "=> Setting executable permissions for $app_name..."
    if [ -f "$DIST_DIR/$app_name" ]; then
        chmod +x "$DIST_DIR/$app_name"
    fi
}

# Main script execution
echo "========= OnTheSpot macOS Build Script =========="

remove_previous_apps
clean_build_dirs
create_virtual_env
activate_virtual_env
install_requirements

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

echo "=> Cleaning up..."
deactivate
clean_build_dirs

echo "=> Build complete!"
