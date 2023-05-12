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

# Usage

Example script in this project:

1. Copy `export.json.example` file to `export.json`
2. Set your Clickhouse database connection params
3. Run `export.py`

Code:

```python
#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import os
from clickhouse_ddl.Config import Config
from clickhouse_ddl.ClickHouseDDL import ClickHouseDDL

if __name__ == '__main__':
    Config.Parse({
        "threads": 8,
        "path_git": "git",
        "new_line": "\n",
        "connect": {
            "host": "localhost",
            "port": 9000,
            "database": "default",
            "username": "user_name",
            "password": "pass_word"
        }
    })

    # Export to folder
    path_result = os.path.join(os.path.dirname(os.path.abspath(__file__)), "result")
    ddl = ClickHouseDDL(path_result)
```

# Links

* [GitHub](https://github.com/ish1mura/clickhouse_ddl)
* [PyPI](https://pypi.org/project/clickhouse-ddl/)
