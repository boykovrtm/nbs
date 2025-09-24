DEPENDS(
    cloud/blockstore/apps/server
    cloud/blockstore/tests/recipes/nbs

    contrib/ydb/apps/ydbd
)

DATA(
    arcadia/cloud/blockstore/tests/certs/server.crt
    arcadia/cloud/blockstore/tests/certs/server.key
)

USE_RECIPE(
    cloud/blockstore/tests/recipes/nbs/nbs-recipe
    --guest-index $GUEST_INDEX
)
