import argparse
import os
import json
import logging

from library.python.testing.recipe import declare_recipe, set_env

from cloud.blockstore.config.server_pb2 import TServerConfig, TServerAppConfig, TKikimrServiceConfig
from cloud.blockstore.config.discovery_pb2 import TDiscoveryServiceConfig

from cloud.blockstore.tests.python.lib.nbs_runner import LocalNbs
from cloud.blockstore.tests.python.lib.test_base import thread_count, wait_for_nbs_server, recipe_set_env

import yatest.common as yatest_common

PID_FILE_NAME = "local_kikimr_nbs_server_recipe.pid"
pm = yatest_common.network.PortManager()
logger = logging.getLogger(__name__)


def _start_instans(args, index):
    server_app_config = TServerAppConfig()
    server_app_config.ServerConfig.CopyFrom(TServerConfig())
    server_app_config.ServerConfig.ThreadsCount = thread_count()
    server_app_config.ServerConfig.StrictContractValidation = False
    server_app_config.ServerConfig.NbdEnabled = True
    server_app_config.ServerConfig.VhostEnabled = True
    server_app_config.KikimrServiceConfig.CopyFrom(TKikimrServiceConfig())

    certs_dir = yatest_common.source_path('cloud/blockstore/tests/certs')
    set_env("TEST_CERT_FILES_DIR", certs_dir)

    server_app_config.ServerConfig.RootCertsFile = os.path.join(certs_dir, 'server.crt')
    cert = server_app_config.ServerConfig.Certs.add()
    cert.CertFile = os.path.join(certs_dir, 'server.crt')
    cert.CertPrivateKeyFile = os.path.join(certs_dir, 'server.key')

    nbs_port = pm.get_port()
    nbs_secure_port = pm.get_port()

    nbs_binary_path = yatest_common.binary_path("cloud/blockstore/apps/server/nbsd")
    if args.nbs_package_path is not None:
        nbs_binary_path = yatest_common.build_path(
            "{}/usr/bin/blockstore-server".format(args.nbs_package_path)
        )

    instance_list_file = os.path.join(yatest_common.output_path(), "static_instance_{}.txt".format(index))
    with open(instance_list_file, "w") as f:
        print("localhost\t%s\t%s" % (nbs_port, nbs_secure_port), file=f)

    discovery_config = TDiscoveryServiceConfig()
    discovery_config.InstanceListFile = instance_list_file

    with open(os.getenv('YDB_RECIPE_METAFILE'), 'r') as f:
        ydb_meta = json.loads(f.read())

    kikimr_port = ydb_meta['nodes'][0]['grpc_port']
    kikimr_binary_path = ydb_meta['clusters']['binary_path']
    domains_txt = ydb_meta['clusters']['domains_txt']

    nbs = LocalNbs(
        grpc_port=kikimr_port,
        domains_txt=domains_txt,
        server_app_config=server_app_config,
        enable_tls=True,
        load_configs_from_cms=True,
        discovery_config=discovery_config,
        nbs_secure_port=nbs_secure_port,
        nbs_port=nbs_port,
        kikimr_binary_path=kikimr_binary_path,
        nbs_binary_path=nbs_binary_path,
        use_ic_version_check=args.use_ic_version_check,
        config_sub_folder="nbs_configs_{}".format(index)
    )

    kikimr = (

    )

    nbs.setup_cms()



def start(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--nbs-package-path", action='store', default=None)
    parser.add_argument("--use-ic-version-check", action='store_true', default=False)
    parser.add_argument("--nbs-instance-count")
    args = parser.parse_args(argv)

    if args.nbs_instance_count == "$NBS_INSTANCE_COUNT":
        args.nbs_instance_count = 1
    else:
        args.nbs_instance_count = int(args.nbs_instance_count)

    for nbs_index in range(args.nbs_instance_count):
        logger.info("tring to start instance No {}".format(nbs_index))
        _start_instans(args, nbs_index)


def stop(argv):
    return

if __name__ == "__main__":
    declare_recipe(start, stop)
