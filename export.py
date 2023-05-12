#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import os,json
from clickhouse_ddl.Config import Config
from clickhouse_ddl.ClickHouseDDL import ClickHouseDDL

if __name__ == '__main__':
    path_current = os.path.dirname(os.path.abspath(__file__))

    # Read config
    with open(os.path.join(path_current, "export.json")) as rf:
        Config.Parse(json.load(rf))

    # Export DDL to folder
    ddl = ClickHouseDDL(os.path.join(path_current, "result"))
