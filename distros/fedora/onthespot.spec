Name:           onthespot
Version:        1.0.7
Release:        1%{?dist}
Summary:        A music downloader
License:        GPL-2.0
Source0:        onthespot-1.0.7-py3-none-any.whl
Source1:        org.onthespot.OnTheSpot.desktop
Source2:        onthespot.png
BuildArch:      noarch

BuildRequires: python3-devel
BuildRequires: python3-pip

Requires: python3-crunpyroll
Requires: python3-flask
Requires: python3-flask-login
Requires: python3-mutagen
Requires: python3-pillow
Requires: python3-pyqt6
Requires: python3-requests
Requires: python3-urllib3
Requires: yt-dlp

Provides: python3.13dist(librespot) = 0.0.9
Provides: python3.13dist(music-tag) = 0.4.3

%description
A music downloader.

%install
mkdir -p %{buildroot}/usr/lib/python3/site-packages
python3 -m pip install --root %{buildroot} --no-deps --ignore-installed %{SOURCE0}
# Only here because I'm to lazy to write another spec and plan on dropping music-tag
python3 -m pip install --root %{buildroot} --no-deps --ignore-installed librespot music-tag

# Ensure that the executables are installed
mkdir -p %{buildroot}/usr/bin

# Install the desktop file
mkdir -p %{buildroot}/usr/share/applications
install -m 0644 %{SOURCE1} %{buildroot}/usr/share/applications/
install -m 0644 %{SOURCE2} %{buildroot}/usr/share/icons/hicolor/256x256/apps/

%files
%{python3_sitelib}/onthespot*
/usr/bin/onthespot-cli
/usr/bin/onthespot-gui
/usr/bin/onthespot-web
/usr/share/applications/org.onthespot.OnTheSpot.desktop

%changelog
* Sat Nov 30 2024 Justin Donofrio <justin025@protonmail.com> - 1.0.7-1
- Initial package creation
