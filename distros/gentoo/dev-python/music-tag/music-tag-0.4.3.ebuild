# Copyright 1999-2025 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8

PYTHON_COMPAT=( python3_{10..13} pypy3 )
DISTUTILS_USE_PEP517=setuptools

inherit distutils-r1

DESCRIPTION="Simple interface to edit audio file metadata"
HOMEPAGE="
	https://github.com/KristoforMaynard/music-tag/
        https://pypi.org/project/music-tag/
"
SRC_URI="
        https://github.com/KristoforMaynard/music-tag/archive/refs/tags/${PV}.tar.gz
                -> ${P}.tar.gz
"

LICENSE="MIT"
SLOT="0"
KEYWORDS="~amd64"

distutils_enable_tests pytest
