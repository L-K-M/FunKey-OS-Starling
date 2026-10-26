#############################################################
#
# libopk
#
#############################################################

LIBOPK_VERSION = libopk-FunKey-1.0.3
LIBOPK_SITE_METHOD = git
LIBOPK_SITE = https://github.com/FunKey-Project/libopk.git
# Upstream (pcercuei/libopk) ships the GPL-2.0 as LICENSE.txt, which this
# fork dropped. The only notice left is unsqfs.c's, from squashfs-tools
# (GPL-2.0+); licenses/notices.ini adds the GPL-2.0 text.
LIBOPK_LICENSE = GPL-2.0
LIBOPK_LICENSE_FILES = unsqfs.c

LIBOPK_DEPENDENCIES = libini zlib

LIBOPK_INSTALL_STAGING = YES

$(eval $(cmake-package))
