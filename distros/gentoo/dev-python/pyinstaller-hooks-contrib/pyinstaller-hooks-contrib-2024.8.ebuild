# Copyright 1999-2025 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8

PYTHON_COMPAT=( python3_{10..13} pypy3 )
DISTUTILS_USE_PEP517=setuptools

inherit distutils-r1 pypi

MY_P="${PN}-${PV}"
DESCRIPTION="Community maintained hooks for PyInstaller."
HOMEPAGE="
	https://github.com/pyinstaller/pyinstaller-hooks-contrib/
	https://pypi.org/project/pyinstaller-hooks-contrib/
"

LICENSE="GPL-2+"
SLOT="0"
KEYWORDS="~amd64"

distutils_enable_tests pytest
