#!/bin/bash

echo "========= OnTheSpot AppImage Build Script ==========="


echo " => Cleaning up !"
rm -rf dist build


echo " => Fetch Dependencies"
mkdir build
cd build

wget https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage

wget https://github.com/niess/python-appimage/releases/download/python3.12/python3.12.3-cp312-cp312-manylinux2014_x86_64.AppImage
chmod +x python3.12.3-cp312-cp312-manylinux2014_x86_64.AppImage

./python3.12.3-cp312-cp312-manylinux2014_x86_64.AppImage --appimage-extract
mv squashfs-root OnTheSpot.AppDir


echo " => Build OnTheSpot.whl"
cd ..
build/OnTheSpot.AppDir/AppRun -m build


echo " => Prepare OnTheSpot AppImage"
cd build/OnTheSpot.AppDir
./AppRun -m pip install -r ../../requirements.txt
./AppRun -m pip install ../../dist/onthespot-*-py3-none-any.whl

rm AppRun .DirIcon python.png python3.12.3.desktop
cp -t . ../../src/onthespot/resources/icons/onthespot.png ../../src/onthespot/resources/org.onthespot.OnTheSpot.desktop

# Create AppRun Script
echo '#! /bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH=$HERE/usr/bin:$PATH;
export APPIMAGE_COMMAND=$(command -v -- "$ARGV0")
export TCL_LIBRARY="${APPDIR}/usr/share/tcltk/tcl8.6"
export TK_LIBRARY="${APPDIR}/usr/share/tcltk/tk8.6"
export TKPATH="${TK_LIBRARY}"
export SSL_CERT_FILE="${APPDIR}/opt/_internal/certs.pem"
"$HERE/opt/python3.12/bin/python3.12" "-m" "onthespot" "$@"' > AppRun

chmod -R 0755 ../OnTheSpot.AppDir
chmod +x AppRun

echo ' '
echo ' # ffmpeg and ffplay need to be manually added to OnTheSpot.AppDir/usr/bin.'
echo ' # Make sure to run chmod +x on each, binaries can be found here:'
echo ' # https://johnvansickle.com/ffmpeg/'
echo ' '
echo ' => Done adding ffmpeg binaries? (y/n)'

read ffmpeg
case $ffmpeg in
  y)
    sleep 1
    clear
    ;;
esac


echo " => Build OnTheSpot AppImage"

cd ..
./appimagetool-x86_64.AppImage --appimage-extract
squashfs-root/AppRun OnTheSpot.AppDir
mv OnTheSpot-x86_64.AppImage ../dist/OnTheSpot-x86_64.AppImage


echo " => Done "
