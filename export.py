#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from argparse import ArgumentParser
import os
from clickhouse_ddl.ClickHouseDDL import ClickHouseDDL

PATH_CURRENT = os.path.dirname(os.path.abspath(__file__))

if __name__ == '__main__':
    parser = ArgumentParser()

    parser.add_argument(
        "-c", "--config",
        help = "Path to config file",
        default = os.path.join(PATH_CURRENT, "config.json"),
    )

    parser.add_argument(
        "-n", "--connect",
        help = "Connect name from config file",
        default = "default",
    )

    parser.add_argument(
        "-f", "--folder",
        help = "Path to result folder",
        default = os.path.join(PATH_CURRENT, "result"),
    )

    args = parser.parse_args()

    ClickHouseDDL(
        path_config  = args.config,
        path_result  = args.folder,
        connect_name = args.connect,
    )
