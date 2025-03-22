#!/bin/bash

echo "========= OnTheSpot AppImage Build Script ==========="


echo " => Cleaning up !"
rm -rf dist build


echo " => Fetch Dependencies"
mkdir build
cd build

curl -L -o appimagetool-x86_64.AppImage https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage

curl -L -o python.AppImage https://github.com/niess/python-appimage/releases/download/python3.12/python3.12.9-cp312-cp312-manylinux2014_x86_64.AppImage
chmod +x python.AppImage

./python.AppImage --appimage-extract
mv squashfs-root OnTheSpot.AppDir


echo " => Build OnTheSpot.whl"
cd ..
build/OnTheSpot.AppDir/AppRun -m build


echo " => Prepare OnTheSpot AppImage"
cd build/OnTheSpot.AppDir
./AppRun -m pip install -r ../../requirements.txt
./AppRun -m pip install ../../dist/onthespot-*-py3-none-any.whl

rm AppRun .DirIcon python.png python*.desktop usr/share/applications/python*.desktop

cp -t . ../../src/onthespot/resources/icons/onthespot.png ../../src/onthespot/resources/org.onthespot.OnTheSpot.desktop
cp ../../src/onthespot/resources/org.onthespot.OnTheSpot.desktop usr/share/applications/

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

cp $(which ffmpeg) ../OnTheSpot.AppDir/usr/bin
cp $(which ffplay) ../OnTheSpot.AppDir/usr/bin

cp /usr/lib/x86_64-linux-gnu/libxcb-cursor.so* ../OnTheSpot.AppDir/usr/lib/
cp /usr/lib/x86_64-linux-gnu/libxcb-xinerama.so* ../OnTheSpot.AppDir/usr/lib/
cp /usr/lib/x86_64-linux-gnu/libxcb.so* ../OnTheSpot.AppDir/usr/lib/
cp /usr/lib/x86_64-linux-gnu/libxcb.so* ../OnTheSpot.AppDir/usr/lib/
cp /usr/lib/x86_64-linux-gnu/libgssapi_krb5.so* ../OnTheSpot.AppDir/usr/lib

echo " => Build OnTheSpot AppImage"
cd ..
./appimagetool-x86_64.AppImage --appimage-extract
squashfs-root/AppRun OnTheSpot.AppDir

mv OnTheSpot-x86_64.AppImage ../dist/OnTheSpot-x86_64.AppImage


echo " => Done "
