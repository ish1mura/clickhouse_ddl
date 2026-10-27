from clickhouse_ddl.System import QuoteName

class TableColumn:
    def __init__(self, data):
        self.DB = data.get("database")

        self.Table = data.get("table")
        self.TableFull = ".".join([self.DB, self.Table])

        self.Name = data.get("name")
        self.NameSQL = QuoteName(self.Name)

        self.Type = data.get("type")

        self.Comment = (data.get("comment") or "").strip()

        default_kind = (data.get("default_kind") or "").strip()
        default_expression = (data.get("default_expression") or "").strip()
        if default_kind == "DEFAULT" and len(default_expression) > 0:
            self.Default = f"{default_kind} {default_expression}"
        else:
            self.Default = ""

    def GetDDL(self):
        comment = f" COMMENT '{self.Comment}'" if len(self.Comment) > 0 else ""
        return f"  {self.NameSQL} {self.Type}{self.Default}{comment}"
