#############################################################
#
# libxdgmime
#
#############################################################
LIBXDGMIME_VERSION = db79e7c
LIBXDGMIME_SITE_METHOD = git
LIBXDGMIME_SITE = https://github.com/FunKey-Project/libxdgmime.git
LIBXDGMIME_DEPENDENCIES = shared-mime-info
# The source headers offer either license; neither text is in the tree.
LIBXDGMIME_LICENSE = AFL-2.0 or LGPL-2.0+
LIBXDGMIME_LICENSE_FILES = README src/xdgmime.h

LIBXDGMIME_INSTALL_STAGING = YES

LIBXDGMIME_MAKE_ENV = CFLAGS="$(TARGET_CFLAGS)" LDFLAGS="$(TARGET_LDFLAGS)" \
				  CROSS_COMPILE="$(TARGET_CROSS)" PREFIX=/usr \
				  PLATFORM="$(BR2_VENDOR)"

define LIBXDGMIME_BUILD_CMDS
	$(LIBXDGMIME_MAKE_ENV) $(MAKE) -C $(@D)
endef

define LIBXDGMIME_INSTALL_STAGING_CMDS
	$(LIBXDGMIME_MAKE_ENV) DESTDIR="$(STAGING_DIR)" $(MAKE) -C $(@D) install
endef

define LIBXDGMIME_INSTALL_TARGET_CMDS
	$(LIBXDGMIME_MAKE_ENV) DESTDIR="$(TARGET_DIR)" $(MAKE) -C $(@D) install-lib
endef

$(eval $(generic-package))
