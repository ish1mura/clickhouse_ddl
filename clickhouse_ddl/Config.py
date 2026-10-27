#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import os

class Config():
    Connects = {}

    Threads = 4

    NL = chr(10)

    @staticmethod
    def Parse(path):
        assert os.path.exists(path), \
            f"Config file '{path}' is not exists"

        with open(path, "r", encoding="utf-8") as rf:
            data = json.loads(rf.read())

        assert data is not None, \
            "Config file is empty"

        assert isinstance(data, dict), \
            "Config file must contains dict"

        assert len(data or {}) > 0, \
            "Config file is empty"

        Config.Connects = data.get("connects") or Config.Connects
        assert len(Config.Connects.keys()) > 0, \
            "No connects in config"

        Config.Threads = data.get("threads") or Config.Threads

        Config.NL = data.get("new_line") or Config.NL
