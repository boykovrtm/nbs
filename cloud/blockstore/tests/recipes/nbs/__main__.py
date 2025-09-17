import argparse
import grpc
import json
import signal
import os
import time
import logging

from library.python.testing.recipe import declare_recipe, set_env

from cloud.blockstore.config.server_pb2 import TServerConfig, TServerAppConfig, TKikimrServiceConfig
from cloud.blockstore.config.discovery_pb2 import TDiscoveryServiceConfig

from google.protobuf.json_format import ParseDict

from cloud.blockstore.tests.python.lib.nbs_runner import LocalNbs
from cloud.blockstore.tests.python.lib.test_base import thread_count, wait_for_nbs_server, recipe_set_env

import contrib.ydb.core.protos.grpc_pb2_grpc as grpc_server
from contrib.ydb.core.protos import config_pb2
from cloud.storage.core.tests.common import (
    append_recipe_err_files,
    process_recipe_err_files,
)

import yatest.common as yatest_common


PID_FILE_NAME = "local_kikimr_nbs_server_recipe.pid"
ERR_LOG_FILE_NAMES_FILE = "local_kikimr_nbs_server_recipe.err_log_files"
pm = yatest_common.network.PortManager()
logger = logging.getLogger(__name__)


class KikimrCluster(object):
    def __init__(self, server, port, retry_count=10):
        self.server = server
        self.port = port
        self.__retry_count = retry_count
        self.__retry_sleep_seconds = 10
        self._options = [
            ('grpc.max_receive_message_length', 64 * 10 ** 6),
            ('grpc.max_send_message_length', 64 * 10 ** 6)
        ]
        self._channel = grpc.insecure_channel("%s:%s" % (self.server, self.port), options=self._options)
        self._stub = grpc_server.TGRpcServerStub(self._channel)

    def invoke(self, request, method):
        retry = self.__retry_count
        while True:
            try:
                callee = getattr(self._stub, method)
                return callee(request)
            except (RuntimeError, grpc.RpcError):
                retry -= 1

                if not retry:
                    raise

                time.sleep(self.__retry_sleep_seconds)


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

    with open(os.getenv(set_guest_index('YDB_RECIPE_METAFILE', index)), 'r') as f:
        ydb_meta = json.loads(f.read())

    kikimr_host = list(ydb_meta['nodes'].values())[0]['host']
    kikimr_port = list(ydb_meta['nodes'].values())[0]['grpc_port']
    kikimr_binary_path = ydb_meta['clusters']['binary_path']
    config = config_pb2.TAppConfig()
    ParseDict(ydb_meta['clusters']['domains_txt'], config.DomainsConfig)
    domains_txt = config.DomainsConfig

    logger.info("meta file has: host {}, port {}, path {}, domains txt {}".format(kikimr_host, kikimr_port, kikimr_binary_path, domains_txt))

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

    kikimr = KikimrCluster(
        kikimr_host,
        kikimr_port
    )

    nbs.setup_cms(kikimr)
    nbs.start()

    append_recipe_err_files(ERR_LOG_FILE_NAMES_FILE, nbs.stderr_file_name)

    recipe_set_env("LOCAL_KIKIMR_KIKIMR_SERVER_PORT", str(kikimr_port), index)
    recipe_set_env("LOCAL_KIKIMR_SECURE_NBS_SERVER_PORT", str(nbs.nbs_secure_port), index)
    recipe_set_env("LOCAL_KIKIMR_INSECURE_NBS_SERVER_PORT", str(nbs.nbs_port), index)

    return nbs


def set_guest_index(content, index=None):
    if index == None:
        return content

    return "{}__{}".format(content, index)


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
    set_env("CLUSTERS_COUNT", args.nbs_instance_count)

    nbs_servers =[]

    for nbs_index in range(args.nbs_instance_count):
        logger.info("tring to start instance No {}".format(nbs_index))
        nbs_servers.append(_start_instans(args, nbs_index))

    with open(PID_FILE_NAME, "w") as f:
        for nbs in nbs_servers:
            f.write(str(nbs.pid) + "\n")

    for nbs in nbs_servers:
        wait_for_nbs_server(nbs.nbs_port)


def stop(argv):
    with open(PID_FILE_NAME) as f:
        for line in f:
            pid = int(line.strip())
            os.kill(pid, signal.SIGTERM)
    errors = process_recipe_err_files(ERR_LOG_FILE_NAMES_FILE)
    if errors:
        raise RuntimeError("Errors during recipe execution:\n" + "\n".join(errors))

if __name__ == "__main__":
    declare_recipe(start, stop)
