# Copyright 1999-2025 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8

PYTHON_COMPAT=( python3_{10..13} pypy3 )
DISTUTILS_USE_PEP517=setuptools

inherit distutils-r1

MY_P="${PN}-python-${PV}"
DESCRIPTION="Open Source Spotify Client"
HOMEPAGE="
	https://github.com/kokarare1212/librespot-python
        https://pypi.org/project/librespot/
"
SRC_URI="
        https://github.com/kokarare1212/librespot-python/archive/refs/tags/v${PV}.tar.gz
                -> ${MY_P}.tar.gz
"
S=${WORKDIR}/${MY_P}

LICENSE="Apache-2.0"
SLOT="0"
KEYWORDS="~amd64"

DEPEND="
        dev-python/defusedxml
        dev-python/pycryptodomex
        dev-python/websocket-client
        dev-python/zeroconf
"

distutils_enable_tests pytest
