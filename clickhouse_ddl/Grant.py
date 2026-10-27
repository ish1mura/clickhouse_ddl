class Grant:
    def __init__(self, data: dict):
        self.RoleName = data.get("role_name").strip()

        self.AccessType = (data.get("access_type") or "").strip().upper()

        self.DB = (data.get("database") or "*").strip()

        self.Table = (data.get("table") or "*").strip()

        self.TableFull = f"{self.DB}.{self.Table}" if self.DB != "*" and self.Table != "*" else ""

        self.Column = (data.get("column") or "").strip()

        self.IsGrantOption = ((data.get("grant_option") or 0) == 1)

    def GetDDL(self):
        grant_option = " WITH GRANT OPTION" if self.IsGrantOption else ""
        return f"GRANT {self.AccessType}{self.Column} ON {self.DB}.{self.Table} TO {self.RoleName}{grant_option};"
