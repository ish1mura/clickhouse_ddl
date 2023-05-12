#!/usr/bin/python
# -*- coding: utf-8 -*-

class Config():
    NL = chr(10)
    Connect = {}
    Threads = 8
    PathGit = "git"

    @staticmethod
    def Parse(json):
        Config.NL = json.get("new_line") or chr(10)
        Config.Connect = json.get("connect") or {}
        Config.Threads = json.get("threads") or 8
        Config.PathGit = json.get("path_git") or "git"
