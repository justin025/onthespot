# Copyright 1999-2025 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8

PYTHON_COMPAT=( python3_{10..13} pypy3 )
DISTUTILS_USE_PEP517=poetry

inherit distutils-r1

DESCRIPTION="Python implementation of Google's Widevine DRM CDM"
HOMEPAGE="
	https://github.com/devine-dl/pywidevine/
        https://pypi.org/project/pywidevine/
"
SRC_URI="
        https://github.com/devine-dl/pywidevine/archive/refs/tags/v${PV}.tar.gz
                -> ${P}.tar.gz
"

DEPEND="
	dev-python/pymp4
"

LICENSE="GPL-3"
SLOT="0"
KEYWORDS="~amd64"

distutils_enable_tests pytest
