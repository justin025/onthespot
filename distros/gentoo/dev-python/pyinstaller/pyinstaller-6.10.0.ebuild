# Copyright 1999-2025 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8

PYTHON_COMPAT=( python3_{10..13} pypy3 )
DISTUTILS_USE_PEP517=setuptools

inherit distutils-r1 pypi

DESCRIPTION="Freeze Python programs into stand-alone executables"
HOMEPAGE="
	https://github.com/pyinstaller/pyinstaller/
	https://pypi.org/project/pyinstaller/
"

LICENSE="GPL-2+"
SLOT="0"
KEYWORDS="~amd64"

DEPEND="
        dev-python/altgraph
        dev-python/setuptools
        dev-python/packaging
        dev-python/pyinstaller-hooks-contrib
"

distutils_enable_tests pytest
