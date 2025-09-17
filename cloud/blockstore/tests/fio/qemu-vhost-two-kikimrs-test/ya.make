PY3TEST()

IF (OPENSOURCE)
    INCLUDE(${ARCADIA_ROOT}/cloud/storage/core/tests/recipes/large.inc)
ELSE()
    INCLUDE(${ARCADIA_ROOT}/cloud/storage/core/tests/recipes/medium.inc)
ENDIF()

TAG(ya:manual)

SET(NBS_INSTANCES_COUNT 2)
SET(VIRTIOFS_SERVER_COUNT 2)

RESOURCE(cloud/blockstore/tests/fio/qemu-vhost-two-kikimrs-test/dynamic_storage_pools.json dynamic_storage_pools)

DEPENDS(
    cloud/storage/core/tools/testing/fio/bin
)

PEERDIR(
    cloud/blockstore/tests/python/lib
    cloud/storage/core/tools/testing/fio/lib
)

TEST_SRCS(
    test.py
)

INCLUDE(${ARCADIA_ROOT}/cloud/blockstore/tests/recipes/ydb/ydb.inc)
INCLUDE(${ARCADIA_ROOT}/cloud/blockstore/tests/recipes/nbs/nbs.inc)
INCLUDE(${ARCADIA_ROOT}/cloud/blockstore/tests/recipes/endpoint/vhost-endpoint.inc)
INCLUDE(${ARCADIA_ROOT}/cloud/blockstore/tests/recipes/qemu.inc)

END()
