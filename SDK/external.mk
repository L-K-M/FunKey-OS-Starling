include $(sort $(wildcard $(BR2_EXTERNAL_SDK_PATH)/package/*/*.mk))

# See FunKey/external.mk: the submodule's tinyalsa.hash has the wrong NOTICE
# hash for the tinyalsa it builds, which fails legal-info.
TINYALSA_HASH_FILE = $(BR2_EXTERNAL_SDK_PATH)/../licenses/tinyalsa.hash
