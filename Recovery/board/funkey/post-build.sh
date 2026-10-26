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

# Change dropbear init sequence
mv ${TARGET_DIR}/etc/init.d/S50dropbear ${TARGET_DIR}/etc/init.d/S42dropbear

# Redirect drobear keys to /tmp
rm -rf ${TARGET_DIR}/etc/dropbear
ln -s /tmp ${TARGET_DIR}/etc/dropbear

# Generate U-Boot environment for app
${HOST_DIR}/bin/mkenvimage -p 0x0 -s 0x20000 -o ${BINARIES_DIR}/u-boot-env.img ${TARGET_DIR}/etc/u-boot.env

# Generate U-Boot environment for production
cp ${TARGET_DIR}/etc/u-boot.env ${TARGET_DIR}/etc/u-boot-prod.env
echo "assembly_tests=1" >> ${TARGET_DIR}/etc/u-boot-prod.env
${HOST_DIR}/bin/mkenvimage -p 0x0 -s 0x20000 -o ${BINARIES_DIR}/u-boot-env-prod.img ${TARGET_DIR}/etc/u-boot-prod.env
rm ${TARGET_DIR}/etc/u-boot-prod.env

# Third-party notices, from the legal-info the top-level Makefile collects
# before the build. notices.py fails, and with it the build, when a package
# has no license text.
python3 "${BR2_EXTERNAL_RECOVERY_PATH}/../licenses/notices.py" \
	--config "${BR2_EXTERNAL_RECOVERY_PATH}/../licenses/notices.ini" \
	--stamp "${STARLING_STAMP:?is unset; build through the top-level Makefile}" \
	--title "Recovery root filesystem" \
	--legal-info "${BASE_DIR}/legal-info" \
	--build-dir "${BUILD_DIR}" \
	--output "${TARGET_DIR}/usr/share/licenses/Third-Party-Notices.txt" || exit 1
