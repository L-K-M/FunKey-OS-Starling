#!/bin/sh

# Add local path to init scripts
sed -i '3iexport PATH=/sbin:/usr/sbin:/bin:/usr/bin:/usr/local/sbin:/usr/local/bin' ${TARGET_DIR}/etc/init.d/rcK
sed -i '3iexport PATH=/sbin:/usr/sbin:/bin:/usr/bin:/usr/local/sbin:/usr/local/bin' ${TARGET_DIR}/etc/init.d/rcS

# Remove log daemon init scripts since they are loaded from inittab
rm -f ${TARGET_DIR}/etc/init.d/S01syslogd ${TARGET_DIR}/etc/init.d/S02klogd

# Remove dhcp lib dir and link to /tmp
rm -rf ${TARGET_DIR}/var/lib/dhcp/
ln -s /tmp ${TARGET_DIR}/var/lib/dhcp

# Remove dhcpcd dir and link to /tmp
rm -rf ${TARGET_DIR}/var/db/dhcpcd/
ln -s /tmp ${TARGET_DIR}/var/db/dhcpcd

# Redirect drobear keys to /tmp
rm -rf ${TARGET_DIR}/etc/dropbear
ln -s /tmp ${TARGET_DIR}/etc/dropbear

# Change dropbear init sequence
mv ${TARGET_DIR}/etc/init.d/S50dropbear ${TARGET_DIR}/etc/init.d/S42dropbear

# Third-party notices, from the legal-info the top-level Makefile collects
# before the build, plus the emulator cores picoarch built and the fonts and
# sounds of the overlay. notices.py fails, and with it the build, when any of
# them has no license text.
python3 "${BR2_EXTERNAL_FUNKEY_PATH}/../licenses/notices.py" \
	--config "${BR2_EXTERNAL_FUNKEY_PATH}/../licenses/notices.ini" \
	--stamp "${STARLING_STAMP:?is unset; build through the top-level Makefile}" \
	--title "FunKey root filesystem" \
	--legal-info "${BASE_DIR}/legal-info" \
	--build-dir "${BUILD_DIR}" \
	--target-dir "${TARGET_DIR}" \
	--cores-dir "$(echo "${BUILD_DIR}"/picoarch-*)" \
	--overlay "${BR2_EXTERNAL_FUNKEY_PATH}/board/funkey/rootfs-overlay" \
	--output "${TARGET_DIR}/usr/share/licenses/Third-Party-Notices.txt" || exit 1
