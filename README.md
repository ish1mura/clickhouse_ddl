# ClickHouse DDL Parser

# Description

Clickhouse metadata (DDL) grabber

# Dependencies

* [Python 3](https://www.python.org/downloads/)
* [clickhouse-driver](https://pypi.org/project/clickhouse-driver/)

# Installation

```bash
pip install clickhouse_ddl
```

# Config file

```jsonc
{
    // Connects (Required)
    "connects": {
        "default": {
            "host": "localhost",
            "port": 9000,
            "database": "default",
            "username": "some_user",
            "password": "some_password"
        }
    },

    // File writing threads (Optional)
    "threads": 8,

    // Newline symbol in files (Optional)
    "new_line": "\n"
}
```

# Export DB to files

From command-line:

```bash
python "export.py" -h
#   usage: export.py [-h] [-c CONFIG] [-n CONNECT] [-f FOLDER]
#   options:
#       -h, --help            show this help message and exit
#       -c, --config CONFIG   Path to config file
#       -n, --connect CONNECT Connect name from config file
#       -f, --folder FOLDER   Path to result folder

python "export.py" -c /some/path/to/config.json -n connect_name -f /some/path/to/result
```

From python script:

```py
from clickhouse_ddl.ClickHouseDDL import ClickHouseDDL

ClickHouseDDL(
    path_config  = "/some/path/to/config.json",
    path_result  = "/some/path/to/result",
    connect_name = "connect_name",
)
```

Check files in `/some/path/to/result`.

# Links

* [GitHub](https://github.com/ish1mura/clickhouse_ddl)
* [PyPI](https://pypi.org/project/clickhouse-ddl/)
