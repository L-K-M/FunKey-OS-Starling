include $(sort $(wildcard $(BR2_EXTERNAL_FUNKEY_PATH)/package/*/*.mk))

# legal-info checks each license file against its package's hash file, and
# the buildroot submodule's tinyalsa.hash has the NOTICE hash of upstream
# tinyalsa 1.1.1 rather than of the FunKey-Project 30d4711 it builds. Point
# tinyalsa at a copy with the right one until the submodule's is fixed.
# Recipes read this variable when they run, so setting it here, after
# buildroot defined the package, takes effect.
TINYALSA_HASH_FILE = $(BR2_EXTERNAL_FUNKEY_PATH)/../licenses/tinyalsa.hash
