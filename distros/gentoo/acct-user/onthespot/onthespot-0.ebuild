# Copyright 2024-2025 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8

inherit acct-user

DESCRIPTION="User for the system wide media-sound/onthespot server"
ACCT_USER_ID=-1
ACCT_USER_HOME=/var/lib/onthespot
ACCT_USER_HOME_PERMS=0750
ACCT_USER_GROUPS=( onthespot )
ACCT_USER_SHELL=/bin/sh

acct-user_add_deps
