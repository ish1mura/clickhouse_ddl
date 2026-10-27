#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from clickhouse_ddl.Config import Config
from clickhouse_ddl.System import QuoteName

class Table(object):
    def __init__(self, data):
        self.DB = data.get("database")

        self.Name = data.get("name")

        self.NameSQL = ".".join([self.DB, QuoteName(self.Name)])

        self.NameFull = ".".join([self.DB, self.Name])

        self.Comment = (data.get("comment") or "").strip()

        self.Columns = []

        self.Grants = []

        self.Engine = data.get("engine_full")
        self.Engine = self.Engine.replace(" PARTITION BY", f"{Config.NL}PARTITION BY")
        self.Engine = self.Engine.replace(" PRIMARY KEY", f"{Config.NL}PRIMARY KEY")
        self.Engine = self.Engine.replace(" ORDER BY", f"{Config.NL}ORDER BY")
        self.Engine = self.Engine.replace(" SETTINGS", f"{Config.NL}SETTINGS")

    def GetDDL(self):
        ddl = f"-- Table: {self.NameSQL}"
        ddl += Config.NL + Config.NL
        ddl += f"-- DROP TABLE IF EXISTS {self.NameSQL};"
        ddl += Config.NL + Config.NL
        ddl += f"CREATE TABLE {self.NameSQL}("
        ddl += Config.NL
        ddl += f",{Config.NL}".join([i.GetDDL() for i in self.Columns])
        ddl += Config.NL
        ddl += ")"
        ddl += Config.NL
        ddl += f"ENGINE = {self.Engine}"

        if len(self.Comment) > 0:
            ddl += Config.NL
            ddl += f"COMMENT '{self.Comment}'"

        ddl += ";"

        if len(self.Grants) > 0:
            ddl += Config.NL + Config.NL
            for grant in self.Grants:
                ddl += grant + Config.NL

        return ddl.strip() + Config.NL
