ENV(YDB_DRIVER_BINARY="contrib/ydb/apps/ydbd/ydbd")

DEPENDS(
    contrib/ydb/apps/ydbd
    cloud/blockstore/tests/recipes/ydb
)

ENV(YDB_ENABLE_PQCD="true")

USE_RECIPE(
    cloud/blockstore/tests/recipes/ydb/ydb-recipe
    --use-log-files
    --guest-index 0
)

USE_RECIPE(
    cloud/blockstore/tests/recipes/ydb/ydb-recipe
    --use-log-files
    --guest-index 1
)
