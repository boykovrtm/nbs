ENV(YDB_DRIVER_BINARY="contrib/ydb/apps/ydbd/ydbd")

DEPENDS(
    contrib/ydb/apps/ydbd
    cloud/blockstore/tests/recipes/ydb
)

USE_RECIPE(
    cloud/blockstore/tests/recipes/ydb/ydb-recipe
    --use-log-files
    --guest_index 0
)

USE_RECIPE(
    cloud/blockstore/tests/recipes/ydb/ydb-recipe
    --use-log-files
    --guest_index 1
)
