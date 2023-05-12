#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from clickhouse_ddl.Config import Config

class Function(object):
    def __init__(self, data):
        self.Name = data.get("name")

        self.Query = data.get("create_query")

        text_as = " AS "
        text_arrow = " -> "

        start_as = self.Query.find(text_as) + len(text_as)
        start_arrow = self.Query.find(text_arrow) + len(text_arrow)

        self.Params = self.Query[start_as:start_arrow - len(text_arrow)]
        self.Params = self.Params.replace("(", "").replace(")", "")
        self.Params = self.Params.split(", ")

        self.Definition = self.Query[start_arrow:]
        if self.Definition.find("(") == 0:
            self.Definition = self.Definition[1:-1]

    def GetDDL(self):
        ddl = "-- Function: {0}".format(self.Name)
        ddl += Config.NL + Config.NL
        ddl += "-- DROP FUNCTION IF EXISTS {0};".format(self.Name)
        ddl += Config.NL + Config.NL
        ddl += f"CREATE FUNCTION {self.Name} AS"
        ddl += Config.NL
        ddl += "  ({0}) ->".format(", ".join(self.Params))
        ddl += Config.NL
        ddl += f"  ({self.Definition})"
        ddl += ";"
        return ddl
