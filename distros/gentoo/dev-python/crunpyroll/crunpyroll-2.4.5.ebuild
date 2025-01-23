# Copyright 1999-2024 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8

PYTHON_COMPAT=( python3_{10..13} pypy3 )
DISTUTILS_USE_PEP517=setuptools

inherit distutils-r1

MY_P="${PN}-python-${PV}"
DESCRIPTION="Open Source Spotify Client"
HOMEPAGE="
	https://github.com/justin025/crunpyroll
        https://pypi.org/project/crunpyroll/
"
SRC_URI="
        https://github.com/justin025/crunpyroll/archive/refs/tags/v${PV}.tar.gz
                -> ${MY_P}.tar.gz
"

LICENSE="Apache-2.0"
SLOT="0"
KEYWORDS="~amd64"

DEPEND="
        dev-python/requests
        dev-python/xmltodict
"

distutils_enable_tests pytest
